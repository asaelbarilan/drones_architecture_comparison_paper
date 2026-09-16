"""Audit two completed SPF verifier preflights without inference."""

import asyncio
import base64
import gzip
import io
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from uavlab.analysis.flight_debugger import _sources, html_document, load_run

OUT = Path("reports/c2_c3_preflight_20260916")


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


async def main():
    freeze = read(OUT / "FREEZE.json")
    runs = []
    audits = []
    for variant in ["c2", "c3"]:
        root = Path("runs") / f"{variant}_visible_preflight_20260916_s1061"
        dest = OUT / variant
        dest.mkdir(exist_ok=True)
        manifest = read(root / "manifest.json")
        assert manifest["architecture_config"] == freeze["architectures"][variant]
        assert manifest["environment_config"] == freeze["environment"]
        replay = await load_run(root)
        assert replay["provenance"]["max_position_error_m"] == 0
        assert replay["provenance"]["missing_source_frames"] == 0
        frames = {f["observation_seq"]: f for f in replay["frames"]}
        calls = [read(p) for p in sorted((root / "debug/calls").glob("*.json"))]
        for c in calls:
            assert c["model_id"] == "qwen3-vl:4b" and c["role"] == "policy"
            assert len(c["image_files"]) == 1
            actual = Image.open(root / c["image_files"][0]).convert("RGB")
            frame = Image.open(
                io.BytesIO(base64.b64decode(frames[c["observation_seq"]]["rgb"].split(",")[1]))
            ).convert("RGB")
            assert np.array_equal(np.asarray(actual), np.asarray(frame))
        es = [
            json.loads(x) for x in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        audit = dict(
            variant=variant,
            name=replay["name"],
            result=replay["result"],
            provenance=replay["provenance"],
            poses=len(replay["frames"]),
            source_images=len(calls),
            completed_calls=sum(c["status"] == "complete" for c in calls),
            cancelled_calls=sum(c["status"] == "cancelled" for c in calls),
            closest_m=min(f["distance"] for f in replay["frames"]),
            outputs=[
                dict(
                    t=c["started_t_sim_ns"] / 1e9,
                    seq=c["observation_seq"],
                    status=c["status"],
                    response=c.get("response"),
                )
                for c in calls
            ],
            stop_events=[
                e
                for e in es
                if e["event_type"] == "decision_proposed"
                and e["payload"].get("kind") == "mission_directive"
            ],
        )
        (dest / "AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        (dest / "events.jsonl.gz").write_bytes(
            gzip.compress((root / "events.jsonl").read_bytes(), mtime=0)
        )
        for name in ["manifest.json", "result.json"]:
            shutil.copy2(root / name, dest / name)
        shutil.copytree(root / "debug", dest / "debug", dirs_exist_ok=True)
        (dest / "replay.json").write_text(json.dumps(replay), encoding="utf-8")
        runs.append(replay)
        audits.append(audit)
    page = html_document(dict(schema=1, runs=runs, sources=_sources()))
    banner = (
        '<div style="padding:12px 24px;background:#18303d;color:#e3f5ff">'
        "D-126: C2 SPF / C3 SPF+verifier. Visible-target preflight, "
        "shared local model and 240s budget. Not clutter capability. "
        "C3 ended below the altitude floor; original saved detail is retained.</div>"
    )
    Path("reports/debugger/c2_c3_preflight.html").write_text(
        page.replace("<body>", "<body>" + banner, 1), encoding="utf-8"
    )
    print(
        json.dumps(
            [
                dict(
                    variant=a["variant"],
                    result=a["result"]["success"],
                    time=a["result"]["sim_duration_s"],
                    distance=a["result"]["metrics"]["distance_to_goal_m"],
                    images=a["source_images"],
                )
                for a in audits
            ]
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
