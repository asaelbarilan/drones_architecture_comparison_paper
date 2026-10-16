"""Long saved-input D141/full-graph comparison; no flights or weight updates."""

import argparse
import os
import threading

from probe_qwen_fast_worker import ExperimentalBackend
from probe_qwen_kernels import cases_for
from probe_qwen_stream import measure, save

from uavlab.plugins.inference.cpu_placement import placed_cpu
from uavlab.plugins.inference.cpu_qos import execution_qos


def verify(backend, out):
    cases = cases_for(backend)
    versions = [(n, p._version) for n, p in backend.model.named_parameters()]
    rows = []
    for repeat in range(25):
        for index, request in enumerate(cases):
            results = {}
            for enabled in ((False, True) if repeat % 2 else (True, False)):
                backend.enabled = enabled
                results[str(enabled)] = measure(backend, request, "first_action")
            reference, candidate = results["False"], results["True"]
            equal = all(reference[k] == candidate[k] for k in ("tokens", "actions"))
            rows.append(dict(repeat=repeat, case=index, reference=reference,
                             candidate=candidate, equal=equal))
            save(out / "pairs.json", rows)
            if not equal:
                raise ValueError("First-action mismatch")
        print(f"paired repeat {repeat + 1}/25", flush=True)
    chunks = []
    for index, request in enumerate(cases):
        backend.enabled = False
        reference = measure(backend, request, "stream_chunk")
        backend.enabled = True
        candidate = measure(backend, request, "stream_chunk")
        equal = all(reference[k] == candidate[k] for k in ("tokens", "actions"))
        chunks.append(dict(case=index, reference=reference, candidate=candidate, equal=equal))
    save(out / "verification.json", dict(
        chunks=chunks, all_equal=all(r["equal"] for r in rows + chunks),
        model_loads=backend.load_count,
        versions_unchanged=versions == [(n, p._version)
                                       for n, p in backend.model.named_parameters()],
        all_frozen=all(not p.requires_grad for p in backend.model.parameters()),
        peak_allocated_bytes=backend.torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=backend.torch.cuda.max_memory_reserved()))


def main():
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--cache-tokens", type=int, default=512)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(420, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    backend = ExperimentalBackend(args.package, args.out / "warmup.json",
                                  pilot_cuda_graphs=True, burst_capacity=args.cache_tokens)
    try:
        with placed_cpu("performance"), execution_qos("latency"):
            backend._load()
            verify(backend, args.out)
    except Exception as error:
        save(args.out / "failure.json", dict(error=repr(error)))
        raise
    finally:
        backend.close()
        timer.cancel()


if __name__ == "__main__":
    main()
