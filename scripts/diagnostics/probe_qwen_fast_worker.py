"""Actual worker check of experimental full graphs; saved inputs, no flights."""

import argparse
import asyncio
import json
import threading
from pathlib import Path

import probe_qwen_worker_latency as worker_probe
from probe_qwen_decoder_graph import DecoderGraph, action_head
from probe_qwen_kernels import variant
from probe_qwen_stream import measure
from probe_qwen_worker_latency import pump, replay, saved_requests
from qwen_action_burst_probe import ActionBurst
from qwen_vision_graph_probe import VisionGraph

from uavlab.live_qwen.latency import qualify
from uavlab.plugins.inference.qwen_worker import QwenWorker
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


class ExperimentalBackend(SharedQwenInference):
    def _load(self):
        if self.model is not None:
            return
        super()._load()
        self.enabled = False
        self.setup_graphs()
        requests = saved_requests(self.model_id)
        checks = []
        for case in ("forward", "turn"):
            request = requests[case, "pilot"]
            self.enabled = False
            reference = measure(self, request, "stream_chunk")
            self.enabled = True
            candidate = measure(self, request, "stream_chunk")
            equal = reference["tokens"] == candidate["tokens"]
            checks.append(dict(case=case, equal=equal, reference=reference, candidate=candidate))
            if not equal:
                raise ValueError("Startup full-chunk action equivalence failed")
        self.warmup_path.write_text(json.dumps(checks, indent=2))

    def __init__(self, package_path, warmup_path, **options):
        self.bf16_norms = options.pop("bf16_norms", False)
        self.burst_capacity = options.pop("burst_capacity", 512)
        super().__init__(package_path, **options)
        self.warmup_path = Path(warmup_path)

    def setup_graphs(self):
        self.decoder = next(m for m in self.model.modules()
                            if type(m).__name__ == "Qwen3VLTextModel")
        self.visual = next(m for m in self.model.modules()
                           if type(m).__name__ == "Qwen3VLVisionModel")
        self.full_graph = DecoderGraph(self.decoder, self.torch)
        self.vision_graph = VisionGraph(self.visual, self.torch)
        self.head, self.full_graph.head = action_head(self)
        self.head_original = self.head.forward
        self.bursts = ActionBurst(self, self.full_graph)
        self.norms = []
        if self.bf16_norms:
            for name, parameter in self.model.named_parameters():
                if "norm" in name and parameter.dtype == self.torch.float32:
                    reduced = parameter.data.to(self.torch.bfloat16)
                    if not self.torch.equal(parameter.data, reduced.float()):
                        raise ValueError("Norm conversion would change stored weight values")
                    self.norms.append((parameter, parameter.data, reduced))

    def _generate(self, request, batch, **kwargs):
        if not self.enabled or request.role != "pilot":
            return super()._generate(request, batch, **kwargs)
        try:
            for parameter, _, reduced in self.norms:
                parameter.data = reduced
            self.decoder.forward = self.full_graph
            self.visual.forward = self.vision_graph
            self.head.forward = self.full_graph.head_forward
            with variant(self, "expanded"):
                return self.bursts.generate(request, batch, **kwargs)
        finally:
            for parameter, original, _ in self.norms:
                parameter.data = original
            self.decoder.forward = self.full_graph.original
            self.visual.forward = self.vision_graph.original
            self.head.forward = self.head_original


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bf16-norms", action="store_true")
    parser.add_argument("--cache-tokens", type=int, default=512)
    parser.add_argument("--poll-ms", type=float, default=20)
    args = parser.parse_args()
    worker_probe.POLL_S = args.poll_ms / 1000
    args.out.mkdir(parents=True, exist_ok=False)
    worker = QwenWorker(dict(package_path=args.package, max_new_tokens=128,
                             warmup_path=str(args.out / "warmup.json"),
                             cpu_placement="performance", cpu_qos="latency",
                             bf16_norms=args.bf16_norms, burst_capacity=args.cache_tokens),
                        factory=ExperimentalBackend)
    worker.start()
    timer = threading.Timer(300, worker.process.terminate)
    timer.daemon = True
    timer.start()
    try:
        ready = pump(worker, ready=True)
        requests = saved_requests("qwen3-vl-4b-d207-shared")
        replay(worker, requests, args.out, repeats=3)
        gates = asyncio.run(qualify(worker, requests["forward", "pilot"],
                                   dict(pilot_ttl_s=1.5, control_hz=20), lambda row: None))
        (args.out / "result.json").write_text(json.dumps(dict(ready=ready, gate=gates), indent=2))
    finally:
        worker.close()
        timer.cancel()


if __name__ == "__main__":
    main()
