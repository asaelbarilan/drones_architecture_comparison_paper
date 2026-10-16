"""Audit D143 actual paths, role calls and first-action latency without rerunning."""

import argparse
import json
import math
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

ROLES = ("planner", "direction", "pilot", "monitor")
COLORS = ("tab:blue", "tab:orange", "tab:green", "tab:red")


def timing(values):
    return dict(count=len(values), median=statistics.median(values), maximum=max(values)) \
        if values else dict(count=0, median=None, maximum=None)


def inspect(folder):
    rows = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
    submitted = {r["request_id"]: r for r in rows if r["kind"] == "submitted"}
    first_actions = {}
    for row in rows:
        if row["kind"] == "action_received":
            first_actions.setdefault(row["packet"]["request_id"], row)
    produced, delivered = [], []
    for identity, row in first_actions.items():
        start = submitted[identity]["wall_ns"]
        produced.append((row["packet"]["ready_ns"]-start)/1e9)
        delivered.append((row["wall_ns"]-start)/1e9)
    consumed = [r for r in rows if r["kind"] == "action_consumed"]
    audit = dict(first_action_produced_s=timing(produced),
                 first_action_received_s=timing(delivered),
                 actions_consumed=len(consumed),
                 all_consumed_fresh=all(r["wall_ns"] < r["packet"]["expires_ns"]
                                        and r["until_ns"] <= r["packet"]["expires_ns"]
                                        for r in consumed),
                 failures=[r for r in rows if r["kind"] in ("contract_failure", "failure")],
                 goals=[r for r in rows if r["kind"] == "goal_authorized"],
                 results=[r for r in rows if r["kind"] == "result" and r["role"] != "pilot"])
    return rows, audit


def draw_case(axes, rows, case):
    ticks = [r for r in rows if r["kind"] == "tick"]
    start = ticks[0]["wall_ns"]
    seconds = [(r["wall_ns"]-start)/1e9 for r in ticks]
    positions = [r["position"] for r in ticks]
    angle = ticks[0]["yaw"]
    x = [(p["x"]-positions[0]["x"])*math.cos(angle)
         + (p["y"]-positions[0]["y"])*math.sin(angle) for p in positions]
    z = [p["z"]-positions[0]["z"] for p in positions]
    yaw = [-math.degrees(r["yaw"]-ticks[0]["yaw"]) for r in ticks]
    axes[0].plot(seconds, x, label="forward displacement")
    axes[0].plot(seconds, z, label="altitude change")
    axes[0].axhline(case["expected_delta"][0], ls="--", color="black", label="forward target")
    axes[0].axhspan(case["expected_delta"][0]-.5, case["expected_delta"][0]+.5, alpha=.1)
    axes[0].set(ylabel="Meters", title=case["id"], xlabel="Seconds")
    axes[0].legend(fontsize=8)
    axes[1].plot(seconds, yaw)
    axes[1].axhline(case["expected_delta"][3], ls="--", color="black")
    axes[1].axhspan(case["expected_delta"][3]-5, case["expected_delta"][3]+5, alpha=.1)
    axes[1].set(ylabel="Clockwise degrees", xlabel="Seconds", title="Heading vs target")
    sources = {r["request_id"]: r for r in rows if r["kind"] == "submitted"}
    for row in rows:
        if row["kind"] != "done":
            continue
        source = sources[row["request_id"]]
        axes[2].barh(ROLES.index(source["role"]), (row["wall_ns"]-source["wall_ns"])/1e9,
                     left=(source["wall_ns"]-start)/1e9, color=COLORS[ROLES.index(source["role"])])
    axes[2].set(yticks=range(4), yticklabels=ROLES, xlabel="Seconds", title="Real role calls")
    for axis in axes:
        axis.grid(alpha=.2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    settings = json.loads((args.root / "config.json").read_text())
    figure, axes = plt.subplots(len(settings["missions"]), 3, figsize=(14, 7),
                                layout="constrained", squeeze=False)
    audits = {}
    for index, case in enumerate(settings["missions"]):
        rows, audits[case["id"]] = inspect(args.root / case["id"])
        draw_case(axes[index], rows, case)
    figure.suptitle("D143 real shared-Qwen architecture — rendered grid3d, not AirSim")
    figure.savefig(args.root / "architecture_results.png", dpi=140)
    plt.close(figure)
    (args.root / "verification_local.json").write_text(json.dumps(audits, indent=2))
    print(json.dumps({name: {k: v for k, v in data.items() if k not in ("results", "goals")}
                      for name, data in audits.items()}, indent=2))


if __name__ == "__main__":
    main()
