"""Summarize completed validation runs without additional model calls."""

import json
from collections import Counter
from pathlib import Path

from uavlab.analysis.flight_debugger import _sources, html_document

ROOT = Path("reports/commitment_validation_20260916")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    rows = []
    for seed in [1060, 1062]:
        folder = ROOT / f"s{seed}"
        for variant in ["off", "on"]:
            audit_path = folder / variant / "AUDIT.json"
            if not audit_path.exists():
                continue
            audit = read(audit_path)
            run = Path("runs") / audit["name"]
            es = [
                json.loads(x)
                for x in (run / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            proposals = [
                e
                for e in es
                if e["event_type"] == "decision_proposed"
                and "source_observation_seq" in e["payload"]
            ]
            targets = [
                e for e in proposals if e["payload"]["provenance"].get("waypoint_kind") == "target"
            ]
            rejected = [
                e
                for e in es
                if e["event_type"] == "decision_proposed" and e["payload"].get("rejected")
            ]
            fence = [e for e in rejected if "geofence" in e["payload"].get("reason", "")]
            monitor = [e for e in es if e["event_type"] == "monitor"]
            calls = [read(p) for p in sorted((run / "debug/calls").glob("*.json"))]
            result = audit["result"]
            row = dict(
                seed=seed,
                variant=variant,
                run=audit["name"],
                success=result["success"],
                sim_s=result["sim_duration_s"],
                censored=result["termination_detail"].startswith("diagnostic early stop"),
                final_m=result["metrics"]["distance_to_goal_m"],
                closest_m=audit["closest_m"],
                closest_s=audit["closest_s"],
                collisions=result["metrics"]["collisions"],
                out_of_bounds=result["metrics"]["out_of_bounds"],
                calls=audit["model_calls"],
                poses=len([e for e in es if e["event_type"] == "control"]),
                target_proposals=len(targets),
                first_target_s=targets[0]["t_sim_ns"] / 1e9 if targets else None,
                target_times_s=[e["t_sim_ns"] / 1e9 for e in targets],
                lease_count=len(audit["leases"]),
                monitor_labels=audit["monitor_labels"],
                recoveries=result["metrics"]["recovery_triggers"],
                geofence_rejections=len(fence),
                first_geofence_s=fence[0]["t_sim_ns"] / 1e9 if fence else None,
                last_monitor=monitor[-1]["payload"]["evidence"] if monitor else None,
                rejection_reasons=dict(Counter(e["payload"].get("reason") for e in rejected)),
                last_policy=next(
                    (
                        c
                        for c in reversed(calls)
                        if c["role"] == "policy" and c["status"] == "complete"
                    ),
                    None,
                ),
            )
            (folder / variant / "MECHANISM.json").write_text(
                json.dumps(row, indent=2), encoding="utf-8"
            )
            rows.append(
                {
                    k: v
                    for k, v in row.items()
                    if k
                    not in ["last_policy", "rejection_reasons", "target_times_s", "last_monitor"]
                }
            )
    (ROOT / "SUMMARY.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    if len(rows) == 4:
        runs = [
            read(ROOT / f"s{seed}" / variant / "replay.json")
            for seed in [1060, 1062]
            for variant in ["off", "on"]
        ]
        page = html_document(dict(schema=1, runs=runs, sources=_sources()))
        page = page.replace(
            "run.result.success?'Completed':run.result.termination_reason",
            "run.result.success?'Completed':"
            "(run.result.termination_detail?.startsWith('diagnostic early stop')?"
            "'Diagnostic stop (censored)':run.result.termination_reason)",
        )
        banner = (
            '<div style="padding:12px 24px;background:#18303d;color:#e3f5ff">'
            "D-124: unchanged C5, seeds 1060/1062, commitment off/on, 240s maximum. "
            "Diagnostic stops are censored. "
            '<a style="color:#65d6dd" href="commitment_240_comparison.html">'
            "Earlier successful seed 1061</a> | "
            '<a style="color:#65d6dd" href="c2_c3_preflight.html">C2/C3 preflight</a></div>'
        )
        Path("reports/debugger/commitment_validation.html").write_text(
            page.replace("<body>", "<body>" + banner, 1), encoding="utf-8"
        )
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
