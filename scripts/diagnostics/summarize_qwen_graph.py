"""Summarize bounded graph evidence without inferring flight performance."""

import json
import math
import statistics
from pathlib import Path

ROOT = Path("reports/qwen_graph_20261016")


def read(path):
    return json.loads(path.read_text())


def timing(values):
    values = sorted(values)
    return dict(count=len(values), median_s=statistics.median(values), minimum_s=min(values),
                maximum_s=max(values), empirical_p95_s=values[math.ceil(len(values)*.95)-1])


def output(row):
    if row["role"] != "pilot":
        return [e["payload"] for e in row["events"] if e["kind"] == "result"]
    return [(e["payload"]["tokens"], e["payload"]["step_fru_m_yaw_rad"])
            for e in row["events"] if e["kind"] == "action"]


def compare(rows, baseline):
    checks = []
    for row in rows:
        old = next(r for r in baseline if r["role"] == row["role"]
                   and r["case"] == row["case"] and output(r))
        a, b = output(old), output(row)
        count = min(len(a), len(b))
        checks.append(dict(role=row["role"], case=row["case"], common=count,
                           equal=count > 0 and a[:count] == b[:count]))
    return checks


def main():
    pairs = read(ROOT / "projections/graph.json")
    warm = [r for r in pairs if r["repeat"] > 0]
    worker = read(ROOT / "prepared_worker/calls.json")
    old = read(Path("reports/qwen_residual_20261016/worker_repeat/calls.json"))
    pilot = [r["first_action_s"] for r in worker if r["role"] == "pilot"]
    result = dict(pair_count=len(pairs), all_pairs_equal=all(r["equal"] for r in pairs),
                  warm_reference=timing([r["reference"]["first_action_s"] for r in warm]),
                  warm_graph=timing([r["result"]["first_action_s"] for r in warm]),
                  worker_cold_s=pilot[0], worker_warm=timing(pilot[1:]),
                  outputs=compare(worker, old),
                  worker_gate=read(ROOT / "prepared_worker/result.json"),
                  invariants=read(ROOT / "projections/complete.json"))
    (ROOT / "verification_local.json").write_text(json.dumps(result, indent=2))
    summary = {k: v for k, v in result.items() if k not in {"outputs", "worker_gate"}}
    print(json.dumps(summary, indent=2))
    print("worker_outputs_equal", all(r["equal"] for r in result["outputs"]))


if __name__ == "__main__":
    main()
