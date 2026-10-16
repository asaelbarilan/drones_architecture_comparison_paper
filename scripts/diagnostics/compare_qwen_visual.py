"""Plot actual D146/D147 traces; all geometric truth stays in offline evaluation."""

import argparse
import json
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def read_episode(root):
    folder = root / "red_pillar"
    rows = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
    truth = json.loads((folder / "evaluator_only.json").read_text())
    ticks = [r for r in rows if r["kind"] == "tick"]
    positions = np.array([[r["position"][k] for k in ("x", "y", "z")] for r in ticks])
    distances = np.linalg.norm(positions-np.array(truth["object_position"]), axis=1)
    times = [(r["wall_ns"]-ticks[0]["wall_ns"])/1e9 for r in ticks]
    return rows, times, distances


def role_evidence(rows):
    kinds = Counter(r["kind"] for r in rows)
    return dict(
        waypoint_refreshes=kinds["visual_waypoint_refresh"],
        stop_checks=[r for r in rows if r["kind"] == "visual_stop_verification"],
        cognitive_responses=[r for r in rows if r["kind"] == "result" and r["role"] != "pilot"],
        first_pilot_request=next((r["prompt"] for r in rows
                                 if r["kind"] == "submitted" and r["role"] == "pilot"), None),
        first_pilot_response=next((r["payload"] for r in rows
                                  if r["kind"] == "result" and r["role"] == "pilot"), None),
    )


def draw(before, after, out):
    fig, axes = plt.subplots(1, 3, figsize=(14, 4), layout="constrained")
    axes[0].imshow(Image.open(before / "red_pillar/input_5_0.png"))
    axes[0].scatter(112, 112, marker="x", c="orange", s=90, label="Old model point")
    audit = json.loads((after / "component_audit.json").read_text())
    first = audit["grounding"][0]
    if first.get("model_point"):
        axes[0].scatter(*first["model_point"], marker="+", c="lime", s=100, label="New model point")
    axes[0].set_title("Same starting camera: grounding")
    axes[0].legend(loc="lower left", fontsize=8)
    axes[1].imshow(Image.open(after / "red_pillar/final_camera.png"))
    axes[1].set_title("Final camera from actual repeat")
    for ax in axes[:2]:
        ax.axis("off")
    for root, label in ((before, "D146 before"), (after, "D147 repeat")):
        _, times, distances = read_episode(root)
        axes[2].plot(times, distances, label=label)
    axes[2].axhline(1.5, color="black", ls="--", label="Unchanged success threshold")
    axes[2].set(title="Independent evaluator", xlabel="Seconds", ylabel="Object distance (m)")
    axes[2].legend(fontsize=8)
    fig.savefig(out / "before_after.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--after", type=Path, required=True)
    args = parser.parse_args()
    before = Path("reports/qwen_visual_object_20261017/real_v2")
    rows, _, distances = read_episode(args.after)
    report = role_evidence(rows)
    report["closest_evaluator_distance_m"] = float(min(distances))
    report["result"] = json.loads((args.after / "red_pillar/result.json").read_text())
    (args.after / "role_evidence.json").write_text(json.dumps(report, indent=2))
    draw(before, args.after, args.after.parent)


if __name__ == "__main__":
    main()
