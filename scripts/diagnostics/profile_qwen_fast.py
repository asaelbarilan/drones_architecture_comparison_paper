"""Synchronized stage profile of the current experimental path, not benchmark timing."""

import argparse
import json
import time
from pathlib import Path

from probe_qwen_fast_worker import ExperimentalBackend
from probe_qwen_stream import measure
from probe_qwen_worker_latency import saved_requests

from uavlab.plugins.inference import shared_qwen
from uavlab.plugins.inference.cpu_placement import placed_cpu
from uavlab.plugins.inference.cpu_qos import execution_qos


def timed(name, original, torch, rows):
    def call(*args, **kwargs):
        torch.cuda.synchronize()
        start = time.perf_counter()
        result = original(*args, **kwargs)
        torch.cuda.synchronize()
        rows.append(dict(stage=name, seconds=time.perf_counter()-start))
        return result

    return call


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    backend = ExperimentalBackend(args.package, str(args.out / "warmup.json"))
    with placed_cpu("performance"), execution_qos("latency"):
        try:
            backend._load()
            rows = []
            hooks = [(shared_qwen, "encode_pilot"), (backend.bursts.core, "get_image_features"),
                     (backend.bursts.core, "get_rope_index"), (backend.bursts, "burst"),
                     (backend.full_graph, "prepared")]
            originals = [(obj, name, getattr(obj, name)) for obj, name in hooks]
            for obj, name, original in originals:
                setattr(obj, name, timed(name, original, backend.torch, rows))
            request = saved_requests(backend.model_id)["forward", "pilot"]
            calls = [measure(backend, request, "first_action") for _ in range(5)]
            for obj, name, original in originals:
                setattr(obj, name, original)
            (args.out / "profile.json").write_text(
                json.dumps(dict(stages=rows, calls=calls), indent=2))
        finally:
            backend.close()


if __name__ == "__main__":
    main()
