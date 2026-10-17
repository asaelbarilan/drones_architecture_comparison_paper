"""Render evaluator-only paths and preserve raw evidence for the nine-task screen."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


def rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def task_trace(folder):
    events = rows(folder / "events.jsonl")
    kinds = {"mission_plan_committed", "planner_wakeup", "planner_recovery",
             "failure", "contract_failure", "stop_rejected", "visual_stop_verification",
             "grounding_absent"}
    decisions = [r for r in events if r["kind"] in kinds or
                 (r["kind"] == "result" and r["role"] != "pilot")]
    (folder / "decisions.json").write_text(json.dumps(decisions, indent=2), encoding="utf-8")
    return events


def plot_task(ax, folder, result):
    events = task_trace(folder)
    scene = json.loads((folder / "initial_evaluator_only.json").read_text())
    ticks = [r for r in events if r["kind"] == "tick"]
    for obstacle in scene["obstacles"]:
        x, y, _ = obstacle["center"]
        a, b, _ = obstacle["half"]
        ax.add_patch(Rectangle((x-a, y-b), 2*a, 2*b, color="gray", alpha=.4))
    ax.plot([r["position"]["x"] for r in ticks], [r["position"]["y"] for r in ticks],
            color="#1976d2", label="Actual path")
    for landmark in scene["landmarks"]:
        x, y, _ = landmark["position"]
        ax.scatter(x, y, color="red" if "red" in landmark["label"] else "royalblue", marker="^")
    ax.scatter(*scene["goal"][:2], marker="x", s=60, color="black", label="Initial goal (truth)")
    final = json.loads((folder / "final_evaluator_only.json").read_text())
    if final["goal"] != scene["goal"]:
        ax.scatter(*final["goal"][:2], marker="D", color="black", label="Final moving target")
        ax.legend(fontsize=6, loc="best")
    ax.scatter(0, 0, marker="o", color="green", label="Start")
    ax.scatter(result["status"]["position"]["x"], result["status"]["position"]["y"],
               marker="s", color="#1976d2", label="Finish")
    outcome = "PASS" if result["task_pass"] else "FAIL"
    ax.set_title(f"{folder.name}: {outcome}\n{result['actions_consumed']} actions; "
                 f"{result['status']['distance_to_goal_m']:.2f}m final distance", fontsize=10)
    ax.set_aspect("equal", adjustable="datalim")
    ax.grid(alpha=.25)
    ax.set_xlabel("World east (m)")
    ax.set_ylabel("World north (m)")


def figures(root, results):
    fig, axes = plt.subplots(3, 3, figsize=(15, 12), constrained_layout=True)
    for ax, (name, result) in zip(axes.flat, results.items(), strict=True):
        plot_task(ax, root / name, result)
    fig.suptitle("Frozen shared-Qwen architecture — nine existing tasks, seed 1061\n"
                 "Top-down actual paths and initial obstacles; "
                 "evaluator overlays never supplied to models")
    axes[0, 0].legend(fontsize=6, loc="best")
    fig.savefig(root.parent / "paths.png", dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(3, 3, figsize=(12, 12), constrained_layout=True)
    for ax, name in zip(axes.flat, results, strict=True):
        ax.imshow(plt.imread(root / name / "initial_camera.png"))
        ax.set_title(name)
        ax.axis("off")
    fig.suptitle("Initial camera inputs — no evaluator overlays")
    fig.savefig(root.parent / "initial_views.png", dpi=140)
    plt.close(fig)


def archive(root):
    manifest = {}
    with zipfile.ZipFile(root.parent / "raw_evidence.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(root.rglob("*.jsonl")):
            relative = path.relative_to(root).as_posix()
            data = path.read_bytes()
            manifest[relative] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
            bundle.writestr(relative, data)
    (root.parent / "raw_manifest.json").write_text(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    root = parser.parse_args().root
    results = json.loads((root / "result.json").read_text())
    figures(root, results)
    archive(root)
    print(json.dumps({name: dict(passed=r["task_pass"], actions=r["actions_consumed"],
                                 stopped=r["stopped"], roles=r["role_calls"])
                      for name, r in results.items()}, indent=2))


if __name__ == "__main__":
    main()
