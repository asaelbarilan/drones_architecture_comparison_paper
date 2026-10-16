"""Offline visual grounding/path audit; never supplies scene truth to models."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from audit_qwen_components import archive_logs
from audit_qwen_full_architecture import inspect
from matplotlib.patches import Rectangle
from PIL import Image

from uavlab.live_qwen.grounding import grounded_direction
from uavlab.plugins.reasoning.shared_qwen_pilot import parse_direction


def grounding(folder, rows):
    submitted = {r["request_id"]: r for r in rows if r["kind"] == "submitted"}
    answers = []
    for row in rows:
        if row["kind"] != "result" or row["role"] != "direction":
            continue
        source = submitted[row["request_id"]]
        entry = dict(request_id=row["request_id"], image=source["image_files"][0],
                     response=row["payload"])
        try:
            data = json.loads(row["payload"])
            if "target_visible" in data:
                data = grounded_direction(data)
            if data is None:
                entry.update(visual_grounding=False, reported_visible=False)
                answers.append(entry)
                continue
            if data["kind"] == "visual":
                entry.update(check_pixels(folder / entry["image"], data["target"]))
            else:
                entry["visual_grounding"] = False
        except (ValueError, KeyError, TypeError):
            entry["valid_grounding_response"] = False
        answers.append(entry)
    return answers


def check_pixels(path, target):
    target = parse_direction(target)
    pixels = np.array(Image.open(path).convert("RGB"), dtype=float)
    mask = (pixels[:, :, 0] > 1.5*pixels[:, :, 1]) & (pixels[:, :, 0] > 1.5*pixels[:, :, 2])
    height, width = mask.shape
    x, y = min(width-1, int(target["u"]*width/1000)), min(height-1, int(target["v"]*height/1000))
    ys, xs = np.where(mask)
    truth = [int(xs.min()), int(ys.min()), int(xs.max()+1), int(ys.max()+1)] if len(xs) else None
    return dict(valid_grounding_response=True, visual_grounding=True,
                point_on_red=bool(mask[y, x]), red_pixel_bbox=truth,
                model_point=[x, y], model_box=target.get("box"),
                reported_visible=target.get("target_visible"),
                box_iou=box_overlap(target.get("box"), truth, width, height))


def box_overlap(model_box, truth, width, height):
    if model_box is None or truth is None:
        return None
    a = np.array(model_box)*np.array([width, height, width, height])/1000
    b = np.array(truth)
    extent = np.maximum(0, np.minimum(a[2:], b[2:])-np.maximum(a[:2], b[:2]))
    intersection = float(np.prod(extent))
    union = float(np.prod(a[2:]-a[:2])+np.prod(b[2:]-b[:2])-intersection)
    return intersection/union if union else 0


def draw(root, rows, answers):
    folder = root / "red_pillar"
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
    image = folder / (answers[0]["image"] if answers else "initial_camera.png")
    axes[0].imshow(Image.open(image))
    if answers and answers[0].get("model_point"):
        axes[0].scatter(*answers[0]["model_point"], c="yellow", marker="x", s=80)
        box = answers[0].get("model_box")
        if box:
            w, h = Image.open(image).size
            x0, y0, x1, y1 = np.array(box)*np.array([w, h, w, h])/1000
            axes[0].add_patch(Rectangle((x0, y0), x1-x0, y1-y0, fill=False, edgecolor="yellow"))
    axes[0].set_title("Direction VLM: first camera + proposal")
    axes[1].imshow(Image.open(folder / "final_camera.png"))
    axes[1].set_title("Final actual camera")
    for ax in axes[:2]:
        ax.axis("off")
    truth = json.loads((folder / "evaluator_only.json").read_text())
    ticks = [r for r in rows if r["kind"] == "tick"]
    times = [(r["wall_ns"]-ticks[0]["wall_ns"])/1e9 for r in ticks]
    distances = [np.linalg.norm(np.array([r["position"][k] for k in ("x", "y", "z")])
                               -truth["object_position"])
                 for r in ticks]
    axes[2].plot(times, distances)
    axes[2].axhline(1.5, color="black", ls="--", label="Frozen success distance")
    axes[2].set(xlabel="Seconds", ylabel="Distance to red pillar (m)",
                title="Evaluator-only distance")
    axes[2].legend()
    fig.savefig(root / "visual_results.png", dpi=150)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    root = parser.parse_args().root
    rows, audit = inspect(root / "red_pillar")
    answers = grounding(root / "red_pillar", rows)
    audit["grounding"] = answers
    audit["numeric_overrides"] = [r for r in rows if r["kind"] == "numeric_completion_override"]
    (root / "component_audit.json").write_text(json.dumps(audit, indent=2))
    archive_logs(root, [dict(id="red_pillar")])
    draw(root, rows, answers)
    print(json.dumps(dict(grounding=answers, failures=audit["failures"]), indent=2))


if __name__ == "__main__":
    main()
