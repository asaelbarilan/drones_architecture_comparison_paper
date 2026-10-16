"""Summarize D142 evidence, preserving worker/backend timing boundaries."""

import json
from pathlib import Path

from summarize_qwen_graph import compare, read, timing

ROOT = Path("reports/qwen_decoder_graph_20261016")


def worker_summary(name, old):
    rows = read(ROOT / name / "calls.json")
    pilot = [r for r in rows if r["role"] == "pilot"]
    produced = []
    for row in pilot:
        event = next(e for e in row["events"] if e["kind"] == "action")
        produced.append((event["payload"]["ready_ns"] - row["observed_ns"]) / 1e9)
    return dict(first_delivered_s=pilot[0]["first_action_s"],
                warm_delivered=timing([r["first_action_s"] for r in pilot[1:]]),
                warm_produced=timing(produced[1:]),
                common_outputs=compare(rows, old),
                startup=read(ROOT / name / "warmup.json"),
                ready_and_gate=read(ROOT / name / "result.json"))


def main():
    old = read(Path("reports/qwen_graph_20261016/prepared_worker/calls.json"))
    names = ("worker", "worker_tf32", "worker_norm_precision", "worker_256", "worker_256_poll2")
    result = dict(workers={name: worker_summary(name, old) for name in names
                          if (ROOT / name / "result.json").exists()})
    path = ROOT / "final_256/pairs.json"
    if path.exists():
        pairs = read(path)
        warm = [r for r in pairs if r["repeat"] > 0]
        result["final_256"] = dict(
            count=len(pairs), all_equal=all(r["equal"] for r in pairs),
            reference=timing([r["reference"]["first_action_s"] for r in warm]),
            candidate=timing([r["candidate"]["first_action_s"] for r in warm]))
    (ROOT / "verification_local.json").write_text(json.dumps(result, indent=2))
    for name, worker in result["workers"].items():
        print(name, worker["warm_delivered"], "outputs_equal",
              all(r["equal"] for r in worker["common_outputs"]))
    print("final_256", result.get("final_256"))


if __name__ == "__main__":
    main()
