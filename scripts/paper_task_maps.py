"""Top-down task maps for the paper: one page per task, one panel per architecture.

Each panel shows the evaluator scene (walls at start in grey, walls that appear during the
flight in red), the target(s), and the drone's actual path coloured by flight time, so the
reader can see what happened when. Evaluator data is only drawn here, never given to models.

    python scripts/paper_task_maps.py --seed 1060
"""

import argparse
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle

MATRIX = "reports/paper_matrix_d165"
ABLATION = "reports/paper_ablation_d179"
TRANSFER = "reports/paper_handles_transfer_d181"
ARMS = [("C0", MATRIX, "C0"), ("C1", MATRIX, "C1"), ("C2", MATRIX, "C2"), ("C3", MATRIX, "C3"),
        ("C4", MATRIX, "C4"), ("C5", MATRIX, "C5"), ("C6", MATRIX, "C6"),
        ("C7", MATRIX, "C7"), ("C8", MATRIX, "C8"), ("FULL", MATRIX, "FULL"),
        ("C10", MATRIX, "C10"), ("C13", MATRIX, "C13"),
        ("FULL + H1 H2", ABLATION, "FULL_H12"), ("FULL + H1 H2 H5", ABLATION, "FULL_H125"),
        ("C10 + H1 H2 H5", TRANSFER, "C10_H125"), ("C13 + H1 H2 H5", TRANSFER, "C13_H125")]
TASKS = ["known_goal", "visible_target", "approach_hover", "turn_search", "overturned_vehicle",
         "conditional_gate", "ordered_visit", "closing_passage", "follow_target",
         "obstacle_post", "obstacle_slalom", "obstacle_low_wall"]
COLS = 4
MAX_S = 60.0
MIN_TICKS = 2


def load(folder):
    """Ticks, scenes and result of one flight, or None when it was not flown."""
    if not (folder / "events.jsonl").exists():
        return None
    ticks = []
    for line in (folder / "events.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("kind") == "tick":
            ticks.append(row)
    read = lambda name: json.loads((folder / name).read_text(encoding="utf-8"))  # noqa: E731
    return dict(ticks=ticks, start=read("initial_evaluator_only.json"),
                end=read("final_evaluator_only.json"), result=read("result.json"))


def draw_scene(ax, flight):
    start, end = flight["start"], flight["end"]
    first = {json.dumps(o["center"]) for o in start["obstacles"]}
    for obstacle in end["obstacles"]:
        x, y, _ = obstacle["center"]
        a, b, _ = obstacle["half"]
        late = json.dumps(obstacle["center"]) not in first
        ax.add_patch(Rectangle((x - a, y - b), 2 * a, 2 * b, color="#c62828" if late else "grey",
                               alpha=.55 if late else .4, lw=0))
    for vehicle in start.get("vehicles", []):
        x, y, _ = vehicle["position"]
        ax.text(x, y, "upside\ndown" if vehicle["inverted"] else "upright", fontsize=5,
                ha="center", va="center")
    for landmark in start["landmarks"]:
        x, y, _ = landmark["position"]
        colour = "red" if "red" in landmark["label"] else "royalblue"
        ax.scatter(x, y, color=colour, marker="^", s=40, zorder=4,
                   edgecolor="black" if landmark.get("target") else "none")
    if end["goal"] != start["goal"]:
        (x0, y0), (x1, y1) = start["goal"][:2], end["goal"][:2]
        ax.annotate("", (x1, y1), (x0, y0), arrowprops=dict(arrowstyle="->", color="red"))


def draw_path(ax, flight):
    ticks = flight["ticks"]
    if len(ticks) < MIN_TICKS:
        return None
    xy = np.array([[t["position"]["x"], t["position"]["y"]] for t in ticks])
    seconds = np.array([t["sim_ns"] for t in ticks]) / 1e9
    lines = LineCollection(np.stack([xy[:-1], xy[1:]], axis=1), cmap="viridis",
                           norm=plt.Normalize(0, MAX_S), lw=2, zorder=3)
    lines.set_array(seconds[:-1])
    ax.add_collection(lines)
    ax.scatter(0, 0, marker="o", color="green", s=25, zorder=5)
    ax.scatter(*xy[-1], marker="s", color="black", s=20, zorder=5)
    return lines


def panel(ax, name, flight, bounds):
    if flight is None:
        ax.set_title(f"{name}: not flown", fontsize=8, color="grey")
        ax.axis("off")
        return None
    draw_scene(ax, flight)
    lines = draw_path(ax, flight)
    passed = flight["result"]["task_pass"]
    ax.set_title(f"{name}: {'PASS' if passed else 'FAIL'}", fontsize=8,
                 color="#2e7d32" if passed else "#c62828", fontweight="bold")
    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_aspect("equal")
    ax.grid(alpha=.2)
    ax.tick_params(labelsize=6)
    return lines


def task_bounds(flights):
    xs, ys = [0.0], [0.0]
    for flight in filter(None, flights):
        xs += [t["position"]["x"] for t in flight["ticks"]]
        ys += [t["position"]["y"] for t in flight["ticks"]]
        for obstacle in flight["end"]["obstacles"]:
            xs.append(obstacle["center"][0])
            ys.append(obstacle["center"][1])
        for landmark in flight["start"]["landmarks"]:
            xs.append(landmark["position"][0])
            ys.append(landmark["position"][1])
        xs.append(flight["end"]["goal"][0])
        ys.append(flight["end"]["goal"][1])
    pad = 3.0
    return min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad


def task_page(task, seed):
    flights = [load(Path(root) / f"s{seed}" / arm / task) for _, root, arm in ARMS]
    bounds = task_bounds(flights)
    rows = math.ceil(len(ARMS) / COLS)
    fig, axes = plt.subplots(rows, COLS, figsize=(16, 4 * rows), constrained_layout=True)
    colour = None
    for ax, (name, _, _), flight in zip(axes.flat, ARMS, flights, strict=True):
        colour = panel(ax, name, flight, bounds) or colour
    if colour is not None:
        fig.colorbar(colour, ax=axes, shrink=.4, label="flight time (s)")
    fig.suptitle(f"{task} (seed {seed}): top-down path coloured by time. Grey = walls at start, "
                 "red = walls that appear in flight; triangles = objects (black edge = target); "
                 "green = start, black square = end", fontsize=11)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--out", type=Path, default=Path("reports/paper_maps"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    pdf_path = args.out / f"task_maps_s{args.seed}.pdf"
    with PdfPages(pdf_path) as pdf:
        for task in TASKS:
            fig = task_page(task, args.seed)
            fig.savefig(args.out / f"s{args.seed}_{task}.png", dpi=110)
            pdf.savefig(fig)
            plt.close(fig)
    print(pdf_path)


if __name__ == "__main__":
    main()
