"""Saved-camera monitor controls: reached waypoint with far, unknown or near object."""

import argparse
import base64
import json
import os
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.interfaces import InferenceRequest
from uavlab.live_qwen.visual_progress import VISUAL_MONITOR
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


def cases(root):
    rows = [json.loads(s) for s in (root / "red_pillar/events.jsonl").read_text().splitlines()]
    monitor = next(r for r in rows if r["kind"] == "submitted" and r["role"] == "monitor")
    direction = next(r for r in rows if r["kind"] == "submitted" and r["role"] == "direction")
    initial = next(r["entry"] for r in rows if r["kind"] == "planner_memory"
                   and r["entry"]["event"] == "target_observed")
    context = json.loads(monitor["prompt"].split("Context: ")[-1])
    yield "near", context, monitor["image_files"][0], "stop"
    far = dict(context, object_range_m=initial["range_m"], object_near=False)
    yield "far_waypoint_reached", far, direction["image_files"][0], "continue"
    unknown = dict(far, object_range_m=None, object_evidence_fresh=False)
    yield "unknown_waypoint_reached", unknown, direction["image_files"][0], "continue"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    root = parser.parse_args().root
    backend = SharedQwenInference("D:/drone_vla_pilot/release/hf_fresh_d257/model")
    results = []
    try:
        for case, context, image, expected in cases(root):
            encoded = base64.b64encode((root / "red_pillar" / image).read_bytes()).decode()
            request = InferenceRequest(model_id=backend.model_id, role="monitor",
                                       prompt_hash="d148-monitor-control",
                                       prompt=VISUAL_MONITOR+json.dumps(context),
                                       images=(encoded,), image_count=1)
            payload, tokens = backend._run(request)
            passed = json.loads(payload)["status"] == expected
            results.append(dict(case=case, prompt=request.prompt, image=image, response=payload,
                                expected=expected, passed=passed, tokens=tokens,
                                scope="saved-camera controlled context, not a new flight"))
            (root.parent / "monitor_controls.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(dict(case=case, passed=passed, response=payload)), flush=True)
    finally:
        backend.close()


if __name__ == "__main__":
    main()
