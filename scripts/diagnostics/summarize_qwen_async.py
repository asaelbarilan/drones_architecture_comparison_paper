"""Audit saved D135 simulator events; never rerun inference or rewrite raw evidence."""

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image

COLORS = dict(planner="tab:blue", direction="tab:orange", pilot="tab:green", monitor="tab:red")


def inspect_case(folder):
    rows = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
    submitted = {r["request_id"]: r for r in rows if r["kind"] == "submitted"}
    first = min(r["wall_ns"] for r in rows)
    calls = []
    for row in rows:
        if row["kind"] != "done":
            continue
        source = submitted[row["request_id"]]
        calls.append(dict(role=source["role"], start=(source["wall_ns"]-first)/1e9,
                          duration=(row["wall_ns"]-source["wall_ns"])/1e9,
                          status=row["status"]))
    ticks = [r for r in rows if r["kind"] == "tick"]
    positions = {tuple(r["position"][k] for k in ("x", "y", "z")) for r in ticks}
    image = next(r["image_files"][0] for r in submitted.values() if r.get("image_files"))
    return dict(calls=calls, unique_positions=len(positions), ticks=len(ticks),
                actions=sum(r["kind"] == "action_consumed" for r in rows),
                image=image, all_commands_hold=all(
                    all(r["command"]["velocity"][k] == 0 for k in ("x", "y", "z"))
                    and r["command"]["yaw_rate_rps"] == 0 for r in ticks))


def plot_cases(root, audits, out):
    figure, axes = plt.subplots(2, 2, figsize=(12, 7), layout="constrained")
    for index, (name, data) in enumerate(audits.items()):
        axes[index, 0].imshow(Image.open(root / name / data["image"]))
        axes[index, 0].axis("off")
        axes[index, 0].set_title(f"{name}: actual direction-camera input")
        axis = axes[index, 1]
        for call in data["calls"]:
            row = list(COLORS).index(call["role"])
            axis.barh(row, call["duration"], left=call["start"], color=COLORS[call["role"]])
        axis.set(yticks=range(4), yticklabels=list(COLORS), xlabel="Wall-clock seconds",
                 title=f"{name}: 0 executed actions; task failed", xlim=(0, 60))
        axis.grid(axis="x", alpha=0.2)
    figure.suptitle("Real shared-Qwen local simulator test — safe hover, no successful flight")
    figure.savefig(out, dpi=150)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    audits = {name: inspect_case(args.root / name) for name in ("forward", "turn")}
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "verification_local.json").write_text(json.dumps(audits, indent=2))
    plot_cases(args.root, audits, args.out / "simulator_audit.png")
    print(json.dumps({k: {a: b for a, b in v.items() if a != "calls"}
                      for k, v in audits.items()}, indent=2))


if __name__ == "__main__":
    main()
