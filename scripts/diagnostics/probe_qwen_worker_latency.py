"""Saved D135 role replay through the actual worker; no environment or motion."""

import argparse
import asyncio
import base64
import json
import os
import threading
import time
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.interfaces import InferenceRequest
from uavlab.live_qwen.latency import qualify
from uavlab.plugins.inference.qwen_worker import QwenWorker, WorkItem

NS = 1_000_000_000
POLL_S = 0.02
TIMEOUT_S = 120
PILOT_TTL_S = 1.5


def saved_requests(model_id):
    result = {}
    for case in ("forward", "turn"):
        source = Path("reports/qwen_async_20261016/real_v1") / case
        rows = [json.loads(line) for line in (source / "events.jsonl").read_text().splitlines()]
        for role in ("planner", "direction", "pilot", "monitor"):
            row = next(r for r in rows if r["kind"] == "submitted" and r["role"] == role)
            images = tuple(base64.b64encode((source / p).read_bytes()).decode()
                           for p in row.get("image_files", []))
            result[case, role] = InferenceRequest(model_id=model_id, role=role, prompt_hash="d136",
                                                  prompt=row["prompt"], images=images,
                                                  image_count=len(images))
    return result


def pump(worker, ready=False):
    deadline = time.perf_counter()+TIMEOUT_S
    result = []
    while time.perf_counter() < deadline:
        now = time.perf_counter_ns()
        for event in worker.poll(1, now):
            if event["kind"] == "fatal":
                raise RuntimeError(event["payload"])
            result.append(dict(kind=event["kind"], payload=event["payload"], consumed_ns=now))
        if worker.ready if ready else worker.current is None:
            return result
        time.sleep(POLL_S)
    raise TimeoutError("worker latency probe deadline")


def replay(worker, inputs, out, repeats=1):
    rows = []
    order = [("forward", "pilot"), ("forward", "planner"), ("forward", "direction")]
    order += [(case, "pilot") for case in ("forward", "turn", "forward", "turn")]
    order += [("turn", "monitor"), ("turn", "pilot"), ("forward", "pilot")]
    for index, key in enumerate(order * repeats):
        now = time.perf_counter_ns()
        ttl = PILOT_TTL_S if key[1] == "pilot" else 15
        worker.submit(WorkItem(index, 1, now, now+int(ttl*NS), inputs[key], 8))
        events = pump(worker)
        actions = [e for e in events if e["kind"] == "action"]
        first = (actions[0]["consumed_ns"]-now)/NS if actions else None
        row = dict(case=key[0], role=key[1], observed_ns=now, expires_ns=now+int(ttl*NS),
                   events=events, first_action_s=first)
        rows.append(row)
        (out / "calls.json").write_text(json.dumps(rows, indent=2))
        print(json.dumps({k: v for k, v in row.items() if k != "events"}), flush=True)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--gate-only", action="store_true")
    parser.add_argument("--repeats", type=int, choices=range(1, 4), default=1)
    parser.add_argument("--gate-after", action="store_true")
    parser.add_argument("--pilot-cuda-graphs", action="store_true")
    parser.add_argument("--cpu-placement", choices=("inherit", "performance"), default="inherit")
    parser.add_argument("--cpu-qos", choices=("inherit", "latency"), default="inherit")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    worker = QwenWorker(dict(package_path=args.package, max_new_tokens=128,
                             cpu_placement=args.cpu_placement, cpu_qos=args.cpu_qos,
                             pilot_cuda_graphs=args.pilot_cuda_graphs))
    worker.start()
    timer = threading.Timer(240, worker.process.terminate)
    timer.daemon = True
    timer.start()
    try:
        ready = pump(worker, ready=True)
        inputs = saved_requests("qwen3-vl-4b-d207-shared")
        result = run_checks(worker, inputs, args)
        result["ready"] = ready
        (args.out / "result.json").write_text(json.dumps(result, indent=2))
    finally:
        worker.close()
        timer.cancel()


def run_checks(worker, inputs, args):
    if args.gate_only:
        settings = dict(pilot_ttl_s=PILOT_TTL_S, control_hz=20)
        rows = asyncio.run(qualify(worker, inputs["forward", "pilot"], settings, lambda row: None))
        return dict(passed=True, qualification=rows, scope="non-executing saved-input replay")
    rows = replay(worker, inputs, args.out, args.repeats)
    pilot = [r for r in rows if r["role"] == "pilot"]
    passed = all(r["first_action_s"] is not None and
                 r["first_action_s"] < PILOT_TTL_S for r in pilot)
    result = dict(passed=passed)
    if args.gate_after:
        settings = dict(pilot_ttl_s=PILOT_TTL_S, control_hz=20)
        result["qualification"] = asyncio.run(
            qualify(worker, inputs["forward", "pilot"], settings, lambda row: None))
    return result


if __name__ == "__main__":
    main()
