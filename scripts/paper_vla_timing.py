"""VLA timing per architecture: request -> first action and request -> all 8 actions.

Reads the wall-clock events of every flight: a pilot request's `submitted` time, then each
streamed `action_received` packet. For C7 / C8 also the `vla_line` call (the VLA writes its
own box and progress line). One PNG, three panels, medians labelled. Chunks revoked
before their 8th action are left out of the all-actions panel.

    python scripts/paper_vla_timing.py reports/paper_heldout
"""

import argparse
import json
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

PILOT_ARMS = [("C13", "C13"), ("C13+H", "C13_H125"), ("C10", "C10"), ("C10+H", "C10_H125"),
              ("C7", "C7"), ("C7+H", "C7_H"), ("C8", "C8"), ("C8+H", "C8_H"),
              ("FULL (classical)", "FULL")]
LINE_ARMS = [("C7", "C7"), ("C7+H", "C7_H"), ("C8", "C8"), ("C8+H", "C8_H")]
TTL_S = 1.5
CHUNK = 8
MIN_QUARTILE_N = 4
INK, MUTED, BOX = "#212121", "#757575", "#3f6fb5"


def flight_timings(path):
    """{request_id: dict(role, submitted, actions=[...], result)} from one events file."""
    requests = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        kind = row.get("kind")
        if kind == "submitted":
            requests[row["request_id"]] = dict(role=row["role"], submitted=row["wall_ns"],
                                               actions=[], result=None)
        elif kind == "action_received":
            entry = requests.get(row["packet"]["request_id"])
            if entry is not None:
                entry["actions"].append(row["wall_ns"])
        elif kind == "result" and row.get("request_id") in requests:
            requests[row["request_id"]]["result"] = row["wall_ns"]
    return requests.values()


def collect(root, folder):
    first, full, line = [], [], []
    for path in Path(root).glob(f"s*/{folder}/*/events.jsonl"):
        for entry in flight_timings(path):
            if entry["role"] == "pilot" and entry["actions"]:
                first.append((entry["actions"][0] - entry["submitted"]) / 1e9)
                if len(entry["actions"]) == CHUNK:  # chunks cut short by a revoke are left out
                    full.append((entry["actions"][-1] - entry["submitted"]) / 1e9)
            elif entry["role"] == "vla_line" and entry["result"]:
                line.append((entry["result"] - entry["submitted"]) / 1e9)
    return first, full, line


def whisker_end(values):
    """Where the box plot's upper whisker ends (Q3 + 1.5 IQR, capped at the data)."""
    if len(values) < MIN_QUARTILE_N:
        return max(values)
    q1, _, q3 = statistics.quantiles(values, n=4)
    return max(v for v in values if v <= q3 + 1.5 * (q3 - q1))


def boxes(ax, labels, series, title):
    keep = [(label, values) for label, values in zip(labels, series, strict=True) if values]
    parts = ax.boxplot([v for _, v in keep], vert=False, widths=0.55, showfliers=False,
                       patch_artist=True, medianprops=dict(color=INK, lw=2),
                       boxprops=dict(facecolor="#dbe6f6", edgecolor=BOX, lw=1.2),
                       whiskerprops=dict(color=BOX), capprops=dict(color=BOX))
    ax.set_yticks(range(1, len(keep) + 1), [f"{label}  (n={len(v)})" for label, v in keep])
    span = max(max(v) for _, v in keep) - min(min(v) for _, v in keep)
    for row, (_, values) in enumerate(keep, start=1):
        ax.text(whisker_end(values) + 0.03 * span, row, f"median {statistics.median(values):.2f} s",
                va="center", fontsize=9, color=INK)
    ax.invert_yaxis()
    ax.set_title(title, loc="left", fontsize=12, fontweight="semibold")
    ax.set_xlabel("seconds from request")
    ax.grid(axis="x", color="#eeeeee")
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    return parts


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", type=Path)
    parser.add_argument("--out", type=Path, default=Path("reports/paper_maps/vla_timing.png"))
    args = parser.parse_args()
    plt.rcParams.update({"font.family": "Segoe UI", "font.size": 10})
    data = {folder: collect(args.root, folder) for _, folder in PILOT_ARMS + LINE_ARMS}
    labels = [label for label, _ in PILOT_ARMS]
    fig, axes = plt.subplots(1, 3, figsize=(17, 6), gridspec_kw=dict(width_ratios=[1, 1, 0.9]))
    boxes(axes[0], labels, [data[f][0] for _, f in PILOT_ARMS], "Pilot: request -> first action")
    boxes(axes[1], labels, [data[f][1] for _, f in PILOT_ARMS],
          "Pilot: request -> all 8 actions (complete chunks)")
    for ax in axes[:2]:
        ax.axvline(TTL_S, color=MUTED, ls="--", lw=1)
        ax.text(TTL_S, 0.45, "1.5 s action expiry ", color=MUTED, fontsize=8, ha="right",
                va="center")
    boxes(axes[2], [label for label, _ in LINE_ARMS], [data[f][2] for _, f in LINE_ARMS],
          "VLA alone: request -> box + goal line")
    fig.suptitle(f"VLA timing per architecture ({args.root.name}; wall clock, local GPU, "
                 "one shared Qwen3-VL-4B worker)", fontsize=14, fontweight="bold")
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=120)
    for label, folder in PILOT_ARMS + LINE_ARMS:
        first, full, line = data[folder]
        values = [statistics.median(v) if v else None for v in (first, full, line)]
        print(label, ["-" if v is None else round(v, 3) for v in values], len(first), len(full),
              len(line))
    print(args.out)


if __name__ == "__main__":
    main()
