"""D147 saved-camera prompt ablation; no flight, training or truth in model input."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.interfaces import InferenceRequest
from uavlab.live_qwen.grounding import GROUNDING
from uavlab.live_qwen.prompts import DIRECTION
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

ROOT = Path("reports/qwen_grounding_fix_20261017")
SAVED = Path("reports/qwen_visual_object_20261017/real_v2/red_pillar")
BOX_PROMPT = (
    "Locate the red pillar in this image, including partially cropped objects. "
    "Return ONLY JSON with keys target_visible (boolean) and box "
    "([left,top,right,bottom] integers normalized to 0..1000, or null if absent). "
    "Use the visible object bounds. Do not return a navigation action or example values."
)
CONTEXT = dict(active_objective="Approach the red pillar",
               authorized_target="Approach the red pillar", numeric_target=False)


def cases(refined):
    present = [SAVED / f for f in ("input_5_0.png", "input_19_0.png")]
    if refined:
        present.append(Path("reports/qwen_completion_fix_20261017/real_v5/hold/input_5_0.png"))
        present.append(ROOT / "real_v1/red_pillar/final_camera.png")
    prompts = (("original", DIRECTION + json.dumps(CONTEXT)), ("box_only", BOX_PROMPT))
    if refined:
        prompts = (("runtime_grounding", GROUNDING + json.dumps(CONTEXT)),
                   ("box_only", BOX_PROMPT))
    return [(path, variant, prompt) for path in present for variant, prompt in prompts]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refined", action="store_true")
    refined = parser.parse_args().refined
    ROOT.mkdir(parents=True, exist_ok=True)
    backend = SharedQwenInference("D:/drone_vla_pilot/release/hf_fresh_d257/model")
    rows = []
    try:
        for path, variant, prompt in cases(refined):
            raw = path.read_bytes()
            request = InferenceRequest(
                model_id=backend.model_id, role="direction", prompt_hash="d147-probe",
                prompt=prompt, images=(base64.b64encode(raw).decode(),), image_count=1,
            )
            payload, tokens = backend._run(request)
            row = dict(image=str(path), sha256=hashlib.sha256(raw).hexdigest(),
                       variant=variant, prompt=prompt, payload=payload, tokens=tokens)
            rows.append(row)
            name = "grounding_controls.json" if refined else "grounding_probe.json"
            (ROOT / name).write_text(json.dumps(rows, indent=2))
            print(json.dumps(row), flush=True)
    finally:
        backend.close()


if __name__ == "__main__":
    main()
