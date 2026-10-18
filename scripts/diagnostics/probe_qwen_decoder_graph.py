"""D142 full text-decode graph experiment with fresh static KV, no executed actions."""

import argparse
import os
import threading
from pathlib import Path

from probe_qwen_kernels import cases_for, variant
from probe_qwen_stream import measure, save
from qwen_action_burst_probe import ActionBurst
from qwen_vision_graph_probe import VisionGraph

from uavlab.plugins.inference.cpu_placement import placed_cpu
from uavlab.plugins.inference.cpu_qos import execution_qos
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

MAX_GRAPHS = 8


def clone_tree(value, torch):
    if torch.is_tensor(value):
        return value.clone()
    if isinstance(value, list):
        return [clone_tree(v, torch) for v in value]
    return value


def copy_tree(target, value, torch):
    if torch.is_tensor(value):
        if target.shape != value.shape:
            raise ValueError("Graph input shape changed")
        target.copy_(value)
    elif isinstance(value, list):
        for a, b in zip(target, value, strict=True):
            copy_tree(a, b, torch)


class DecoderGraph:
    def __init__(self, decoder, torch):
        self.decoder, self.torch = decoder, torch
        self.original = decoder.forward
        self.entries = {}
        self.head = None
        self.latest = None
        self.evictions = 0

    def cached(self, key, prepared):
        """Bound memory without making the ninth input shape a fatal mission error."""
        if key in self.entries:
            entry = self.entries.pop(key)
        else:
            if len(self.entries) >= MAX_GRAPHS:
                self.torch.cuda.synchronize()
                self.latest = None
                self.entries.pop(next(iter(self.entries)))
                self.evictions += 1
            entry = self.capture(prepared)
        self.entries[key] = entry
        return entry

    def deepstack(self, hidden, mask, features):
        ranks = (mask.long().cumsum(-1) - 1).clamp_min(0)
        addition = self.torch.where(mask.unsqueeze(-1), features[ranks], 0)
        return hidden + addition

    def prepared(self, kwargs):
        from transformers.masking_utils import create_causal_mask

        result = dict(kwargs)
        position = kwargs["position_ids"][0]
        result["attention_mask"] = create_causal_mask(
            config=self.decoder.config, input_embeds=kwargs["inputs_embeds"],
            attention_mask=kwargs["attention_mask"], cache_position=kwargs["cache_position"],
            past_key_values=kwargs["past_key_values"], position_ids=position)
        return result

    def capture(self, kwargs):
        torch = self.torch
        buffers = {k: clone_tree(v, torch) for k, v in kwargs.items()}
        indices = None
        previous = self.decoder._deepstack_process
        if kwargs.get("visual_pos_masks") is not None:
            self.decoder._deepstack_process = self.deepstack
        try:
            graph, output, logits = self.capture_forward(buffers)
        finally:
            self.decoder._deepstack_process = previous
        return buffers, graph, output, indices, logits

    def capture_forward(self, buffers):
        torch = self.torch
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                self.original(**buffers)
        torch.cuda.current_stream().wait_stream(stream)
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            output = self.original(**buffers)
            logits = self.head(output.last_hidden_state[:, -1:])
        return graph, output, logits

    def __call__(self, *args, **kwargs):
        cache = kwargs["past_key_values"]
        if args or not all(layer.is_initialized for layer in cache.layers):
            return self.original(*args, **kwargs)
        from transformers.modeling_outputs import BaseModelOutputWithPast

        prepared = self.prepared(kwargs)
        key = (kwargs["inputs_embeds"].shape,
               tuple(layer.keys.data_ptr() for layer in cache.layers))
        buffers, graph, output, indices, logits = self.cached(key, prepared)
        for name, value in prepared.items():
            copy_tree(buffers[name], value, self.torch)
        if indices is not None:
            indices.copy_(kwargs["visual_pos_masks"][0].nonzero().flatten())
        graph.replay()
        self.latest = output.last_hidden_state[:, -1:].data_ptr(), logits
        return BaseModelOutputWithPast(last_hidden_state=output.last_hidden_state,
                                       past_key_values=cache)

    def head_forward(self, hidden):
        if self.latest is not None and hidden.data_ptr() == self.latest[0]:
            return self.latest[1]
        return self.head(hidden)


def action_head(backend):
    head = backend.model.get_output_embeddings()
    torch = backend.torch
    high = backend.tokenizer.vocab_size
    low = high - backend.tokenizer.n_bins

    def forward(hidden):
        bias = None if head.bias is None else head.bias[low:high]
        scores = torch.nn.functional.linear(hidden, head.weight[low:high], bias)
        output = torch.full((*scores.shape[:-1], head.out_features), float("-inf"),
                            dtype=scores.dtype, device=scores.device)
        output[..., low:high] = scores
        return output

    return head, forward


def experiment(backend, out):
    cases = cases_for(backend)
    decoder = next(m for m in backend.model.modules() if type(m).__name__ == "Qwen3VLTextModel")
    wrapper = DecoderGraph(decoder, backend.torch)
    visual = next(m for m in backend.model.modules() if type(m).__name__ == "Qwen3VLVisionModel")
    vision = VisionGraph(visual, backend.torch)
    head, fast_head = action_head(backend)
    wrapper.head = fast_head
    original_head, original_generate = head.forward, backend._generate
    burst = ActionBurst(backend, wrapper)
    rows, config = [], backend.model.generation_config
    previous = config.cache_implementation
    try:
        for repeat in range(3):
            for index, request in enumerate(cases):
                decoder.forward = wrapper.original
                visual.forward = vision.original
                head.forward = original_head
                backend._generate = original_generate
                config.cache_implementation = previous
                reference = measure(backend, request, "first_action")
                config.cache_implementation = "static"
                decoder.forward = wrapper
                visual.forward = vision
                head.forward = wrapper.head_forward
                backend._generate = burst.generate
                with variant(backend, "expanded"):
                    result = measure(backend, request, "first_action")
                rows.append(dict(repeat=repeat, case=index, reference=reference, result=result,
                                 equal=reference["tokens"] == result["tokens"] and
                                 reference["actions"] == result["actions"]))
                save(out / "pairs.json", rows)
            print(f"repeat={repeat} graphs={len(wrapper.entries)}", flush=True)
        thread_sweep(backend, cases, rows[:4], out)
    finally:
        decoder.forward = wrapper.original
        visual.forward = vision.original
        head.forward = original_head
        backend._generate = original_generate
        config.cache_implementation = previous


def thread_sweep(backend, cases, references, out):
    rows = []
    original = backend.torch.get_num_threads()
    try:
        for threads in (1, 2, 4, 8, 16):
            backend.torch.set_num_threads(threads)
            for repeat in range(3):
                for index, case in enumerate(cases):
                    with variant(backend, "expanded"):
                        result = measure(backend, case, "first_action")
                    reference = references[index]["reference"]
                    rows.append(dict(threads=threads, repeat=repeat, case=index, result=result,
                                     equal=result["tokens"] == reference["tokens"] and
                                     result["actions"] == reference["actions"]))
            save(out / "threads.json", rows)
            print(f"threads={threads}", flush=True)
    finally:
        backend.torch.set_num_threads(original)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(300, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    backend = SharedQwenInference(args.package)
    try:
        with placed_cpu("performance"), execution_qos("latency"):
            backend._load()
            experiment(backend, args.out)
    except Exception as error:
        save(args.out / "failure.json", dict(error=repr(error)))
        raise
    finally:
        backend.close()
        timer.cancel()


if __name__ == "__main__":
    main()
