"""Saved-input GPU equivalence across more than eight graph shapes; no flights."""

import argparse
import json
import threading
from dataclasses import replace
from pathlib import Path

from probe_qwen_fast_worker import ExperimentalBackend
from probe_qwen_stream import measure
from probe_qwen_worker_latency import saved_requests
from run_qwen_async import deadline_exit

from uavlab.plugins.inference.cpu_placement import placed_cpu
from uavlab.plugins.inference.cpu_qos import execution_qos

CASES = 11


def check_shapes(backend, out):
    request = saved_requests(backend.model_id)["forward", "pilot"]
    rows = []
    for index in range(CASES):
        context = json.loads(request.prompt)
        context["instruction"] += " carefully" * (index+1)
        probe = replace(request, prompt=json.dumps(context))
        backend.enabled = False
        reference = measure(backend, probe, "stream_chunk")
        backend.enabled = True
        candidate = measure(backend, probe, "stream_chunk")
        equal = reference["tokens"] == candidate["tokens"]
        row = dict(index=index, prompt=probe.prompt, equal=equal,
                   reference=reference, candidate=candidate,
                   graph_entries=len(backend.full_graph.entries),
                   evictions=backend.full_graph.evictions)
        rows.append(row)
        (out / "pairs.json").write_text(json.dumps(rows, indent=2))
        print(json.dumps({k: row[k] for k in ("index", "equal", "graph_entries", "evictions")}),
              flush=True)
        if not equal:
            raise AssertionError("cache repair changes sampled action tokens")
    assert backend.full_graph.evictions > 0, "eviction was not exercised"
    return rows


def run(args):
    backend = ExperimentalBackend(args.package, warmup_path=str(args.out / "warmup.json"),
                                  burst_capacity=256, prompt_audit=True)
    try:
        backend._load()
        versions = [(n, p._version) for n, p in backend.model.named_parameters()]
        rows = check_shapes(backend, args.out)
        unchanged = versions == [(n, p._version) for n, p in backend.model.named_parameters()]
        assert unchanged
        (args.out / "result.json").write_text(json.dumps(dict(
            passed=True, pairs=len(rows), weights_unchanged=unchanged,
            evictions=backend.full_graph.evictions, executed_actions=0), indent=2))
    finally:
        backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(300, deadline_exit)
    timer.daemon = True
    timer.start()
    try:
        with placed_cpu("performance"), execution_qos("latency"):
            run(args)
    except Exception as exc:
        (args.out / "failure.json").write_text(json.dumps(dict(error=repr(exc))))
        raise
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
