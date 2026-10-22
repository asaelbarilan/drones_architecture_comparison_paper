"""Top-down task maps for the paper: one page per task, one panel per architecture.

Each panel shows the evaluator scene (walls at start in grey, walls that appear during the
flight in red), the objects, and the drone's actual path coloured by flight time, so the
reader can see what happened when. Rows group the architectures: the reference and the
vanilla stacks without a planner, then the planner stacks, then the same planner stacks with
the handles, each directly below its vanilla version. Page 1 is the architecture legend.
Evaluator data is only drawn here, never given to models.

    python scripts/paper_task_maps.py --seed 1060
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

MATRIX = "reports/paper_matrix_d165"
ABLATION = "reports/paper_ablation_d179"
TRANSFER = "reports/paper_handles_transfer_d181"
CONNECTIONS = "reports/paper_connections_d182"
# (code, short description, run root, run folder); None leaves a slot empty.
ROWS = [
    ("Reference and\nsingle-model", [
        ("C0", "true goal given (privileged)", MATRIX, "C0"),
        ("C1", "LLM calls text skills", MATRIX, "C1"),
        ("C7", "VLA alone", MATRIX, "C7"),
        ("C8", "VLA alone + shield", MATRIX, "C8"), None]),
    ("VLA alone\n+ handles", [
        None, None,
        ("C7+H", "with H4 H9", CONNECTIONS, "C7_H"),
        ("C8+H", "with H4 H9", CONNECTIONS, "C8_H"), None]),
    ("VLM waypoint\nstacks (no planner)", [
        ("C2", "VLM points to a waypoint", MATRIX, "C2"),
        ("C3", "C2 + verifier", MATRIX, "C3"),
        ("C4", "C3 + periodic monitor", MATRIX, "C4"),
        ("C5", "C4 + memory", MATRIX, "C5"),
        ("C6", "C3 + recovery planner", MATRIX, "C6")]),
    ("VLM waypoint\nstacks + handles", [
        (f"{code}+H", "with H3 H4", CONNECTIONS, f"{code}_H")
        for code in ("C2", "C3", "C4", "C5", "C6")]),
    ("Planner stacks", [
        ("FULL", "planner, classical pilot", MATRIX, "FULL"),
        ("C10", "timed planner, VLA pilot", MATRIX, "C10"),
        ("C13", "event planner, VLA pilot", MATRIX, "C13"), None, None]),
    ("Planner stacks\n+ handles", [
        ("FULL+H", "with H1 H2 H5", ABLATION, "FULL_H125"),
        ("C10+H", "with H1 H2 H5", TRANSFER, "C10_H125"),
        ("C13+H", "with H1 H2 H5", TRANSFER, "C13_H125"),
        ("FULL+H1H2", "without H5", ABLATION, "FULL_H12"), None]),
]
LEGEND = [
    ("C0", "Oracle: the true goal is given to a classical pilot. Privileged ceiling."),
    ("C1", "Skill agent: a text-only LLM calls goto / approach / detect / scan / hover."),
    ("C2", "VLM points at the target in the image; the point becomes a waypoint."),
    ("C3", "C2 plus a verifier that checks each waypoint before it is flown."),
    ("C4", "C3 plus a monitor that reviews progress on a timer."),
    ("C5", "C4 plus memory of past goals and outcomes."),
    ("C6", "C3 plus a recovery planner called on events (lost target, stall)."),
    ("C7", "VLA alone: the trained VLA writes its own goal line and flies it."),
    ("C8", "C7 plus the safety shield and envelope verifier."),
    ("FULL", "Planner + VLM grounding + verifier + monitor + event recovery + memory;\n"
             "classical pilot."),
    ("C10", "As FULL, the planner runs on a timer; the VLA is the pilot."),
    ("C13", "As FULL, the planner runs on events; the VLA is the pilot."),
    ("H1", "Handle: typed task contract (visit / pass / condition / follow / goto / search)."),
    ("H2", "Handle: one executive runs the contract by step kind."),
    ("H5", "Handle: measured openings from the range sensor; sensor answers what it can."),
    ("H3", "Handle: a find / search mission starts the bounded camera search itself."),
    ("H4", "Handle: completion on evidence: stated standoff / hold, object passed below."),
    ("H9", "Handle: the VLA picks the target box, the depth sensor gives the distance."),
]
TASKS = ["known_goal", "visible_target", "approach_hover", "turn_search", "overturned_vehicle",
         "conditional_gate", "ordered_visit", "closing_passage", "follow_target",
         "obstacle_post", "obstacle_slalom", "obstacle_low_wall"]
COLS = 5
MAX_S = 60.0
MIN_TICKS = 2
MIN_ASPECT = 0.45
PASS, FAIL, MUTED = "#2e7d32", "#c62828", "#9e9e9e"
STYLE = {"font.family": "Segoe UI", "font.size": 11, "axes.titlesize": 12,
         "axes.edgecolor": "#bdbdbd", "xtick.color": "#616161", "ytick.color": "#616161",
         "xtick.labelsize": 8, "ytick.labelsize": 8}


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
        ax.add_patch(Rectangle((x - a, y - b), 2 * a, 2 * b, lw=0, zorder=1,
                               color="#ef9a9a" if late else "#bdbdbd"))
    for vehicle in start.get("vehicles", []):
        x, y, _ = vehicle["position"]
        ax.annotate("upside down" if vehicle["inverted"] else "upright", (x, y),
                    xytext=(0, 9), textcoords="offset points", ha="center", fontsize=7,
                    color="#424242")
    for landmark in start["landmarks"]:
        x, y, _ = landmark["position"]
        colour = "#e53935" if "red" in landmark["label"] else "#1e88e5"
        ax.scatter(x, y, color=colour, marker="^", s=70, zorder=4,
                   edgecolor="black" if landmark.get("target") else "white", linewidth=1)
    if end["goal"] != start["goal"]:
        (x0, y0), (x1, y1) = start["goal"][:2], end["goal"][:2]
        ax.annotate("", (x1, y1), (x0, y0), zorder=4,
                    arrowprops=dict(arrowstyle="-|>", color="#e53935", lw=1.5, ls="--"))


def draw_path(ax, flight):
    ticks = flight["ticks"]
    ax.scatter(0, 0, marker="o", color="#43a047", s=45, zorder=6, edgecolor="white")
    final = flight["result"]["status"]["position"]
    ax.scatter(final["x"], final["y"], marker="s", color="black", s=35, zorder=5,
               edgecolor="white")
    if len(ticks) < MIN_TICKS:
        return None
    xy = np.array([[t["position"]["x"], t["position"]["y"]] for t in ticks])
    seconds = np.array([t["sim_ns"] for t in ticks]) / 1e9
    lines = LineCollection(np.stack([xy[:-1], xy[1:]], axis=1), cmap="plasma",
                           norm=plt.Normalize(0, MAX_S), lw=3, zorder=3, capstyle="round")
    lines.set_array(seconds[:-1])
    ax.add_collection(lines)
    return lines


def frame(ax, colour):
    for spine in ax.spines.values():
        spine.set_edgecolor(colour)
        spine.set_linewidth(2.5)


def panel(ax, arm, flight, bounds):
    code, text = arm[0], arm[1]
    ax.set_xlim(bounds[0], bounds[1])
    ax.set_ylim(bounds[2], bounds[3])
    ax.set_aspect("equal")
    if flight is None:
        ax.set_title(f"{code}  ·  not flown", color=MUTED, loc="left")
        ax.set_xticks([])
        ax.set_yticks([])
        frame(ax, "#eeeeee")
        return None
    draw_scene(ax, flight)
    lines = draw_path(ax, flight)
    passed = flight["result"]["task_pass"]
    colour = PASS if passed else FAIL
    ax.set_title(f"{code}  ·  {text}", loc="left", fontweight="semibold", fontsize=11)
    ax.text(0.98, 0.04, "PASS" if passed else "FAIL", transform=ax.transAxes, ha="right",
            va="bottom", fontsize=10, fontweight="bold", color="white",
            bbox=dict(boxstyle="round,pad=0.3", fc=colour, ec="none"))
    frame(ax, colour)
    ax.grid(color="#eeeeee", lw=0.8)
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
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    grow = max(0.0, MIN_ASPECT * (x1 - x0) - (y1 - y0)) / 2  # long thin scenes stay readable
    return x0, x1, y0 - grow, y1 + grow


def symbol_legend(fig):
    handles = [Line2D([], [], marker="o", ls="", color="#43a047", label="start"),
               Line2D([], [], marker="s", ls="", color="black", label="end"),
               Line2D([], [], marker="^", ls="", color="#e53935", mec="black", label="target"),
               Line2D([], [], marker="^", ls="", color="#1e88e5", mec="white",
                      label="other object"),
               Patch(color="#bdbdbd", label="wall"),
               Patch(color="#ef9a9a", label="wall that appears in flight"),
               Line2D([], [], color="#e53935", ls="--", label="moving target")]
    fig.legend(handles=handles, loc="upper center", ncol=7, frameon=False, fontsize=11,
               bbox_to_anchor=(0.5, 0.965))


def task_page(task, seed):
    arms = [arm for _, row in ROWS for arm in row]
    flights = [arm and load(Path(arm[2]) / f"s{seed}" / arm[3] / task) for arm in arms]
    bounds = task_bounds(flights)
    fig, axes = plt.subplots(len(ROWS), COLS, figsize=(20, 3.7 * len(ROWS) + 1.8))
    fig.subplots_adjust(left=0.08, right=0.985, top=0.92, bottom=0.06, hspace=0.36, wspace=0.14)
    colour = None
    for ax, arm, flight in zip(axes.flat, arms, flights, strict=True):
        if arm is None:
            ax.axis("off")
            continue
        colour = panel(ax, arm, flight, bounds) or colour
    for row, (label, _) in enumerate(ROWS):
        axes[row, 0].set_ylabel(label, fontsize=12, fontweight="semibold", color="#37474f",
                                labelpad=10)
    passes = sum(1 for f in flights if f and f["result"]["task_pass"])
    flown = sum(1 for f in flights if f)
    fig.suptitle(f"{task.replace('_', ' ')}   (seed {seed}: {passes} of {flown} pass)",
                 fontsize=18, fontweight="bold", y=0.985)
    symbol_legend(fig)
    if colour is not None:
        bar = fig.add_axes([0.3, 0.022, 0.4, 0.008])
        fig.colorbar(colour, cax=bar, orientation="horizontal",
                     label="time since start (s); path colour")
    return fig


def legend_page():
    fig = plt.figure(figsize=(16, 9))
    fig.suptitle("Architectures and handles in the task maps", fontsize=20, fontweight="bold",
                 y=0.95)
    y = 0.85
    for code, text in LEGEND:
        handle = code.startswith("H")
        if code == "H1":
            y -= 0.03
        fig.text(0.06, y, code, fontsize=14, fontweight="bold", va="top",
                 color="#6a1b9a" if handle else "#263238")
        fig.text(0.15, y, text, fontsize=13, va="top", color="#212121")
        y -= 0.07 if "\n" in text else 0.048
    fig.text(0.06, 0.03, "Same model (Qwen3-VL-4B + D207 VLA adapter), runtime, path planner, "
             "shield and tasks in every panel. '+H' = the handles that fit that architecture.",
             fontsize=11, color="#616161")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=1060)
    parser.add_argument("--out", type=Path, default=Path("reports/paper_maps"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(STYLE)
    pdf_path = args.out / f"task_maps_s{args.seed}.pdf"
    with PdfPages(pdf_path) as pdf:
        fig = legend_page()
        fig.savefig(args.out / "legend.png", dpi=110)
        pdf.savefig(fig)
        plt.close(fig)
        for task in TASKS:
            fig = task_page(task, args.seed)
            fig.savefig(args.out / f"s{args.seed}_{task}.png", dpi=110)
            pdf.savefig(fig)
            plt.close(fig)
    print(pdf_path)


if __name__ == "__main__":
    main()
