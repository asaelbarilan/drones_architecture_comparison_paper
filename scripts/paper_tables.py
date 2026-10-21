"""D-166 paper tables: pass rates and costs per architecture x task from the matrix runs.

Reads reports/<matrix>/s<seed>/<arch>/<task>/result.json (+ events.jsonl for call latency) and
writes tables.md / tables.json next to the matrix. Capability and cost stay separate vectors
(EXPERIMENTS.md): success, collisions, stop correctness; model calls by role, median call
latency, mission time. Seeds are paired: the same seed is the same scene for every architecture.

  python scripts/paper_tables.py --matrix reports/paper_matrix_d165
"""

import argparse
import collections
import json
import math
import statistics
from pathlib import Path

ARCHS = ["C0", "C1", "C2", "C3", "C4", "C5", "C6", "FULL", "C7", "C8", "C10", "C13"]
TASKS = ["known_goal", "visible_target", "approach_hover", "turn_search", "overturned_vehicle",
         "conditional_gate", "ordered_visit", "closing_passage", "follow_target",
         "obstacle_post", "obstacle_slalom", "obstacle_low_wall"]
GROUPS = {"basic": TASKS[:3], "perception": TASKS[3:5], "planning": TASKS[5:9],
          "obstacles": TASKS[9:]}
Z = 1.96


def wilson(k, n):
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    centre = (p + Z * Z / (2 * n)) / (1 + Z * Z / n)
    half = Z * math.sqrt(p * (1 - p) / n + Z * Z / (4 * n * n)) / (1 + Z * Z / n)
    return (round(centre - half, 3), round(centre + half, 3))


def call_latencies(events_path):
    """Seconds from submission to result per role, from the run's own event log."""
    submitted, out = {}, collections.defaultdict(list)
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event["kind"] == "submitted":
            submitted[event["request_id"]] = (event["role"], event["wall_ns"])
        elif event["kind"] == "result" and event.get("request_id") in submitted:
            role, start = submitted[event["request_id"]]
            out[role].append((event["wall_ns"] - start) / 1e9)
    return out


def load(matrix):
    rows = []
    for result in sorted(matrix.glob("s*/*/*/result.json")):
        seed, arch, task = result.parts[-4][1:], result.parts[-3], result.parts[-2]
        data = json.loads(result.read_text(encoding="utf-8"))
        status = data["status"]
        events = result.with_name("events.jsonl")
        rows.append(dict(seed=int(seed), arch=arch, task=task, passed=bool(data["task_pass"]),
                         collided=status["collision_count"] > 0, stopped=data["stopped"],
                         distance_m=status["distance_to_goal_m"],
                         sim_s=status["t_sim_ns"] / 1e9, calls=data["role_calls"],
                         latency=call_latencies(events) if events.exists() else {}))
    return rows


def pass_table(rows):
    cells = collections.defaultdict(list)
    for r in rows:
        cells[r["arch"], r["task"]].append(r["passed"])
    lines = ["| arch | " + " | ".join(TASKS) + " | total | 95% CI |",
             "|" + "---|" * (len(TASKS) + 3)]
    summary = {}
    for arch in [a for a in ARCHS if any(k[0] == a for k in cells)]:
        marks, k, n = [], 0, 0
        for task in TASKS:
            got = cells.get((arch, task), [])
            k, n = k + sum(got), n + len(got)
            marks.append(f"{sum(got)}/{len(got)}" if got else "-")
        summary[arch] = dict(passed=k, flights=n, ci=wilson(k, n))
        lines.append(f"| {arch} | " + " | ".join(marks) + f" | {k}/{n} | {wilson(k, n)} |")
    return "\n".join(lines), summary


def group_table(rows):
    lines = ["| arch | " + " | ".join(GROUPS) + " |", "|" + "---|" * (len(GROUPS) + 1)]
    for arch in [a for a in ARCHS if any(r["arch"] == a for r in rows)]:
        marks = []
        for tasks in GROUPS.values():
            got = [r["passed"] for r in rows if r["arch"] == arch and r["task"] in tasks]
            marks.append(f"{sum(got)}/{len(got)}" if got else "-")
        lines.append(f"| {arch} | " + " | ".join(marks) + " |")
    return "\n".join(lines)


def cost_table(rows):
    lines = ["| arch | flights | collisions | model calls / flight | median call s (by role) |"
             " mean mission s |", "|---|---|---|---|---|---|"]
    for arch in [a for a in ARCHS if any(r["arch"] == a for r in rows)]:
        mine = [r for r in rows if r["arch"] == arch]
        calls = statistics.mean(sum(r["calls"].values()) for r in mine)
        roles = collections.defaultdict(list)
        for r in mine:
            for role, values in r["latency"].items():
                roles[role] += values
        median = ", ".join(f"{role} {statistics.median(v):.2f}"
                           for role, v in sorted(roles.items()))
        lines.append(f"| {arch} | {len(mine)} | {sum(r['collided'] for r in mine)} | {calls:.1f} | "
                     f"{median} | {statistics.mean(r['sim_s'] for r in mine):.1f} |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    args = parser.parse_args()
    rows = load(args.matrix)
    passes, summary = pass_table(rows)
    seeds = sorted({r["seed"] for r in rows})
    text = (f"# Paper matrix tables ({len(rows)} flights, seeds {seeds})\n\n## Pass by task\n\n"
            f"{passes}\n\n## Pass by task group\n\n{group_table(rows)}\n\n## Cost\n\n"
            f"{cost_table(rows)}\n")
    (args.matrix / "tables.md").write_text(text, encoding="utf-8")
    plain = [{k: v for k, v in r.items() if k != "latency"} for r in rows]
    (args.matrix / "tables.json").write_text(json.dumps(dict(rows=plain, summary=summary),
                                                        indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
