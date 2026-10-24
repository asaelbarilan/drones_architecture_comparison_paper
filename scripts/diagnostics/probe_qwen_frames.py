"""D-186 detector probe, VLM arm: the runtime's own Qwen grounding on the same frames.

Same frames, objects and scoring as probe_detectors.py (IoU >= 0.5 with the true visible box;
the overturned vehicle must not be confused with the upright one), with the runtime's
GROUNDING prompt and the D207 release model, so the three perception options compare 1:1.

    python scripts/diagnostics/probe_qwen_frames.py
"""

import argparse
import base64
import json
import os
import statistics
import time
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.interfaces import InferenceRequest
from uavlab.live_qwen.grounding import GROUNDING, grounded_direction
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

MODEL = "D:/drone_vla_pilot/release/hf_fresh_d257/model"
NAMES = {"red pillar": "red pillar", "blue pillar": "blue pillar",
         "overturned vehicle": "overturned vehicle", "upright vehicle": "upright vehicle"}
HIT_IOU = 0.5
WARMUP = 3


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def look(backend, image_bytes, name):
    context = dict(active_objective=f"visit {name}", authorized_target=name,
                   numeric_target=False)
    request = InferenceRequest(model_id=backend.model_id, role="direction",
                               prompt_hash="d186-probe", prompt=GROUNDING + json.dumps(context),
                               images=(base64.b64encode(image_bytes).decode(),), image_count=1)
    start = time.perf_counter()
    payload, _ = backend._run(request)
    elapsed = time.perf_counter() - start
    try:
        proposal = grounded_direction(payload)
    except ValueError:
        proposal = None
    return (proposal["target"]["box"] if proposal else None), elapsed, payload


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frames", type=Path, default=Path("reports/detector_probe/frames"))
    frames = json.loads((parser.parse_args().frames / "truth.json").read_text())
    root = Path("reports/detector_probe/frames")
    backend = SharedQwenInference(MODEL)
    rows, times = [], []
    try:
        for frame in frames:
            raw = (root / frame["image"]).read_bytes()
            for label, truth in frame["boxes"].items():
                box, elapsed, payload = look(backend, raw, NAMES[label])
                times.append(elapsed)
                overlap = iou(box, truth) if box else 0.0
                rows.append(dict(image=frame["image"], object=label, iou=round(overlap, 3),
                                 hit=overlap >= HIT_IOU, box=box, payload=payload))
    finally:
        backend.close()
    Path("reports/detector_probe/Qwen3-VL-4B.json").write_text(json.dumps(rows, indent=1))
    pillars = [r for r in rows if "pillar" in r["object"]]
    over = [r for r in rows if r["object"] == "overturned vehicle"]
    timed = times[WARMUP:]
    print(dict(detector="Qwen3-VL-4B (runtime grounding)",
               pillar_hits=f"{sum(r['hit'] for r in pillars)}/{len(pillars)}",
               pillar_mean_iou=round(statistics.mean(r["iou"] for r in pillars), 3),
               overturned_hits=f"{sum(r['hit'] for r in over)}/{len(over)}",
               median_ms=round(1000 * statistics.median(timed), 1)))


if __name__ == "__main__":
    main()
