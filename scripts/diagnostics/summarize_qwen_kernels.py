"""Summarize paired D138 saved-input measurements without model execution."""

import argparse
import json
import math
import statistics
from pathlib import Path

MILLISECONDS = 1000
TAIL_PERCENTILE = 0.95


def distribution(values):
    ordered = sorted(values)
    return dict(n=len(ordered), median_ms=statistics.median(ordered) * MILLISECONDS,
                p95_ms=ordered[math.ceil(TAIL_PERCENTILE * len(ordered))-1] * MILLISECONDS,
                min_ms=min(ordered) * MILLISECONDS, max_ms=max(ordered) * MILLISECONDS)


def summarize(folder):
    pairs = json.loads((folder / "pairs.json").read_text())
    complete = json.loads((folder / "complete.json").read_text())
    roles = json.loads((folder / "roles.json").read_text())
    result = dict(complete=complete, variants={}, matched_contexts=len(pairs),
                  distinct_contexts=len({r["case"] for r in pairs}),
                  all_base_role_outputs_equal=all(r["equals_baseline"] for r in roles),
                  caveat="Backend saved-input latency, not fresh camera-to-controller p95.")
    for name in complete["names"]:
        rows = [row["results"][name]["result"] for row in pairs]
        ratios = [row["results"]["baseline"]["result"]["first_action_s"] /
                  row["results"][name]["result"]["first_action_s"] for row in pairs]
        result["variants"][name] = dict(
            first_action=distribution([r["first_action_s"] for r in rows]),
            first_token=distribution([r["first_token_s"] for r in rows]),
            median_paired_speedup=statistics.median(ratios),
            action_matches=sum(row["equal"][name] for row in pairs))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    result = summarize(args.folder)
    (args.folder.parent / "verification_local.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
