"""Paper audit (2026-10-21): every architecture config -> what it really runs and where it was run.

For each configs/architectures/*.yaml (resolved through its _base_ chain) report the family,
authority, policy / monitor / recovery / verifier plugins, the inference backend and model ids
(simulated = scripted stand-in latency, anything else = a real model call), tags, and which
environments it has actually been run on according to saved manifest.json files under runs/ and
reports/ (episodes counted per environment). Writes JSON + a markdown table; runs nothing.

  python scripts/audit_architectures.py --out reports/paper_audit_20261021
"""

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uavlab.core.compose import load_raw

ROOT = Path(__file__).resolve().parents[1]


def plugin(cfg, key):
    part = cfg.get(key) or {}
    return part.get("name") if isinstance(part, dict) else None


def model_ids(cfg):
    """All model ids named anywhere in the policy / inference / monitor / recovery blocks."""
    found = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k in (
                    "model_id",
                    "model",
                    "monitor_model_id",
                    "reasoner_model_id",
                ) and isinstance(v, str):
                    found.add(v)
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for key in ("policy", "inference", "monitor", "recovery", "verifier", "models"):
        walk(cfg.get(key))
    return sorted(found)


def describe(path):
    cfg = load_raw(path)
    backend = plugin(cfg, "inference") or "none"
    tags = cfg.get("tags") or []
    return dict(
        file=path.stem,
        id=cfg.get("id"),
        family=cfg.get("family"),
        subfamily=cfg.get("subfamily"),
        authority=cfg.get("authority"),
        policy=plugin(cfg, "policy"),
        monitor=plugin(cfg, "monitor"),
        recovery=plugin(cfg, "recovery"),
        verifier=plugin(cfg, "verifier"),
        backend=backend,
        models=model_ids(cfg),
        real_model=backend not in ("simulated", "none", "free"),
        privileged="privileged_diagnostic" in tags
        or bool(cfg.get("allow_privileged_observations")),
        development=any("dev" in t for t in tags) or path.stem.endswith("_dev"),
        scheduler=(cfg.get("scheduler") or {}).get("kind"),
        tags=tags,
    )


def runs_by_config():
    """{architecture file stem or id: Counter(environment name -> manifests)} from saved runs."""
    seen = collections.defaultdict(collections.Counter)
    for manifest in list(ROOT.glob("runs/**/manifest.json")) + list(
        ROOT.glob("reports/**/manifest.json")
    ):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        arch, env = data.get("architecture_config") or {}, data.get("environment_config") or {}
        names = {arch.get("id"), arch.get("name")} - {None}
        env_name = env.get("id") or env.get("name") or "?"
        for name in names:
            seen[name][env_name] += 1
    return seen


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    runs = runs_by_config()
    rows = []
    for path in sorted((ROOT / "configs/architectures").glob("*.yaml")):
        if path.stem.startswith("_"):
            continue
        row = describe(path)
        envs = runs.get(row["id"], collections.Counter())
        row["runs"] = dict(envs)
        row["capability_runs"] = sum(n for e, n in envs.items() if str(e).startswith("capability"))
        rows.append(row)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "architectures.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    head = ["config", "id", "family", "authority", "policy", "backend", "models", "real", "priv"]
    head += ["capability runs", "other envs"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        other = ", ".join(
            f"{e}:{n}" for e, n in sorted(r["runs"].items()) if not str(e).startswith("capability")
        )
        cells = [r["file"], r["id"], r["family"], r["authority"], r["policy"], r["backend"]]
        cells += [", ".join(r["models"]), "Y" if r["real_model"] else "-"]
        cells += ["Y" if r["privileged"] else "-", r["capability_runs"], other]
        lines.append("| " + " | ".join(str(c) for c in cells) + " |")
    (args.out / "architectures.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            dict(
                configs=len(rows),
                real=sum(r["real_model"] for r in rows),
                with_capability_runs=sum(1 for r in rows if r["capability_runs"]),
            )
        )
    )


if __name__ == "__main__":
    main()
