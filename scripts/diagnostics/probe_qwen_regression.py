"""D136 paired saved-input latency isolation; no flights, downloads or training."""

import argparse
import base64
import json
import os
import threading
import time
from collections import Counter
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from probe_qwen_stream import measure, requests

from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.qwen_actions import encode_pilot, read_pilot
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


def inputs(backend):
    config = json.loads(Path("reports/qwen_stream_20261016/real_v2/config.json").read_text())
    old = requests(config, Path("reports/shared_qwen_vla_20261016/final/input.png"),
                   backend.model_id)[0]
    source = Path("reports/qwen_async_20261016/real_v1/forward")
    rows = [json.loads(line) for line in (source / "events.jsonl").read_text().splitlines()]
    row = next(r for r in rows if r["kind"] == "submitted" and r["role"] == "pilot")
    image = base64.b64encode((source / row["image_files"][0]).read_bytes()).decode()
    new = InferenceRequest(model_id=backend.model_id, role="pilot", prompt_hash="d136",
                           prompt=row["prompt"], images=(image,), image_count=1)
    return dict(old=old, new=new)


def inspect_inputs(backend, cases):
    shapes = {}
    for name, request in cases.items():
        start = time.perf_counter()
        batch = encode_pilot(backend, request, read_pilot(request))
        shapes[name] = dict(seconds=time.perf_counter()-start,
                            tensors={k: list(v.shape) for k, v in batch.items()})
    return shapes


def paired(backend, cases, out):
    rows = []
    for name in ("old", "new", "new", "old", "old", "new"):
        result = measure(backend, cases[name], "first_action")
        rows.append(dict(case=name, result=result))
        (out / "pairs.json").write_text(json.dumps(rows, indent=2))
        print(json.dumps(dict(case=name, seconds=result["seconds"],
                              first_token=result["first_token_s"])), flush=True)
    return rows


def profile(backend, request, out):
    torch = backend.torch
    activities = [torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]
    with torch.profiler.profile(activities=activities, record_shapes=True) as prof:
        measure(backend, request, "first_action")
    averages = prof.key_averages()
    for sort in ("self_cpu_time_total", "self_cuda_time_total"):
        table = averages.table(sort_by=sort, row_limit=35)
        clean = "\n".join(line.rstrip() for line in table.splitlines()).rstrip()+"\n"
        (out / f"profile_{sort}.txt").write_text(clean)


def run(args):
    backend = SharedQwenInference(args.package)
    try:
        backend._load()
        cases = inputs(backend)
        identity = dict(torch=backend.torch.__version__,
                        transformers=__import__("transformers").__version__,
                        threads=backend.torch.get_num_threads(),
                        devices=dict(Counter(str(p.device) for p in backend.model.parameters())),
                        shapes=inspect_inputs(backend, cases))
        (args.out / "identity.json").write_text(json.dumps(identity, indent=2))
        paired(backend, cases, args.out)
        profile(backend, cases["new"], args.out)
    finally:
        backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(240, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        run(args)
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
