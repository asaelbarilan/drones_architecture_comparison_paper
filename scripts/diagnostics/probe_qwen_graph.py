"""Bounded pilot-only CUDA graph feasibility; saved inputs, no executed actions."""

import argparse
import os
import threading
from contextlib import contextmanager
from pathlib import Path

from probe_qwen_kernels import cases_for
from probe_qwen_stream import measure, save

from uavlab.plugins.inference.cpu_placement import placed_cpu
from uavlab.plugins.inference.cpu_qos import execution_qos
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


class GraphedMLP:
    def __init__(self, original, torch):
        self.original, self.torch = original, torch
        self.graph = None
        self.replays = 0

    def capture(self, value):
        torch = self.torch
        self.buffer = value.clone()
        stream = torch.cuda.Stream()
        stream.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(stream):
            for _ in range(3):
                self.original(self.buffer)
        torch.cuda.current_stream().wait_stream(stream)
        self.graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(self.graph):
            self.output = self.original(self.buffer)

    def __call__(self, value):
        if value.shape[-2] != 1:
            return self.original(value)
        if self.graph is None:
            self.capture(value)
        self.buffer.copy_(value)
        self.graph.replay()
        self.replays += 1
        return self.output.clone()


@contextmanager
def graph_mlps(backend):
    modules = [m for n, m in backend.model.named_modules()
               if type(m).__name__ == "Qwen3VLTextMLP" or
               ("language_model.layers." in n and
                n.rsplit(".", 1)[-1] in {"q_proj", "k_proj", "v_proj", "o_proj"})]
    originals = [m.forward for m in modules]
    wrappers = [GraphedMLP(f, backend.torch) for f in originals]
    try:
        for module, wrapper in zip(modules, wrappers, strict=True):
            module.forward = wrapper
        yield wrappers, modules, originals
    finally:
        for module, original in zip(modules, originals, strict=True):
            module.forward = original


def experiment(backend, out):
    cases = cases_for(backend)
    baseline = [measure(backend, case, "first_action") for case in cases]
    save(out / "baseline.json", baseline)
    rows = []
    with graph_mlps(backend) as (wrappers, modules, originals):
        for repeat in range(25):
            for index, case in enumerate(cases):
                for module, original in zip(modules, originals, strict=True):
                    module.forward = original
                reference = measure(backend, case, "first_action")
                for module, wrapper in zip(modules, wrappers, strict=True):
                    module.forward = wrapper
                result = measure(backend, case, "first_action")
                rows.append(dict(repeat=repeat, case=index, result=result, reference=reference,
                                 equal=result["tokens"] == reference["tokens"]
                                 and result["actions"] == reference["actions"]))
                save(out / "graph.json", rows)
            print(f"repeat={repeat} calls={len(rows)}", flush=True)
        save(out / "captures.json", [w.replays for w in wrappers])
    save(out / "restored.json", [measure(backend, c, "first_action") for c in cases])


def run(args):
    backend = SharedQwenInference(args.package)
    try:
        with placed_cpu("performance"), execution_qos("latency"):
            backend._load()
            versions = [(n, p._version) for n, p in backend.model.named_parameters()]
            experiment(backend, args.out)
            save(args.out / "complete.json", dict(loads=backend.load_count,
                 frozen=all(not p.requires_grad for p in backend.model.parameters()),
                 unchanged=versions == [(n, p._version)
                                        for n, p in backend.model.named_parameters()],
                 peak_bytes=backend.torch.cuda.max_memory_allocated()))
    except Exception as error:
        save(args.out / "failure.json", dict(error=repr(error)))
        raise
    finally:
        backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(300, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        run(args)
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
