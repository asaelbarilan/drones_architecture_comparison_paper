"""Replay saved pilot requests with only the accumulated-heading state changed.

Answers one question: does the pilot creep because of the heading input
(e.g. 221 deg after search turns) rather than the image or remaining goal?
Same frame, same instruction, same remaining goal; only state[3] varies.
"""

import argparse
import base64
import json
from pathlib import Path

from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


def wrapped(deg):
    return (deg + 180) % 360 - 180


def requests(run_dir, limit):
    rows = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
    pilots = [r for r in rows if r.get("kind") == "submitted" and r.get("role") == "pilot"]
    return [r for r in pilots if (run_dir / f"input_{r['request_id']}_0.png").exists()][:limit]


def forward(backend, prompt, image):
    request = InferenceRequest(model_id=backend.model_id, role="pilot", prompt_hash="probe:heading",
                               prompt=json.dumps(prompt), images=(image,), image_count=1)
    payload, _ = backend._run(request)
    steps = payload["steps_fru_m_yaw_rad"]
    return round(sum(s[0] for s in steps), 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--run", required=True, type=Path, action="append")
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--instruction", help="also replay with this instruction text")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    backend = SharedQwenInference(args.package)
    results = []
    try:
        backend._load()
        for run_dir in args.run:
            for row in requests(run_dir, args.limit):
                image = base64.b64encode(
                    (run_dir / f"input_{row['request_id']}_0.png").read_bytes()).decode("ascii")
                prompt = json.loads(row["prompt"])
                yaw = prompt["state"][3]
                variants = dict(recorded=yaw, wrapped=wrapped(yaw), zero=0.0)
                fwd = {}
                for name, value in variants.items():
                    fwd[name] = forward(backend, dict(prompt, state=[*prompt["state"][:3], value]),
                                        image)
                if args.instruction:
                    fwd["swapped_instruction"] = forward(
                        backend, dict(prompt, instruction=args.instruction), image)
                rem = prompt["remaining"]
                fwd["state_xyz_zero"] = forward(
                    backend, dict(prompt, state=[0.0, 0.0, 0.0, yaw]), image)
                fwd["remaining_up_zero"] = forward(
                    backend, dict(prompt, remaining=[rem[0], rem[1], 0.0, rem[3]]), image)
                fwd["both_zero"] = forward(
                    backend, dict(prompt, state=[0.0, 0.0, 0.0, yaw],
                                  remaining=[rem[0], rem[1], 0.0, rem[3]]), image)
                results.append(dict(run=str(run_dir), request_id=row["request_id"],
                                    yaw_recorded=yaw, remaining=prompt["remaining"],
                                    forward_sum_m=fwd))
                print(json.dumps(results[-1]), flush=True)
    finally:
        backend.close()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
