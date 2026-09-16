"""Replay, image-check and compare the frozen commitment pair without inference."""

import argparse
import asyncio
import base64
import gzip
import hashlib
import io
import json
import math
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image

from uavlab.analysis.flight_debugger import _sources, html_document, load_run

OUT = Path("reports/commitment_pair_20260916")
PAGE = "commitment_240"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def events(root):
    return [json.loads(x) for x in (root / "events.jsonl").read_text(encoding="utf-8").splitlines()]


async def one(variant):
    frozen = read(OUT / "FREEZE.json")
    name = f"c5_commitment_{variant}_240_20260916_s{frozen['seed']}"
    root = Path("runs") / name
    dest = OUT / variant
    dest.mkdir(exist_ok=True)
    frozen = read(OUT / "FREEZE.json")
    manifest = read(root / "manifest.json")
    assert manifest["architecture_config"] == frozen["architectures"][variant]
    assert manifest["environment_config"] == frozen["environment"]
    cache = dest / "replay.json"
    if cache.exists():
        replay = read(cache)
        assert (
            replay["provenance"]["events_sha256"]
            == hashlib.sha256((root / "events.jsonl").read_bytes()).hexdigest()
        )
        assert replay["result"] == read(root / "result.json")
    else:
        replay = await load_run(root)
    (dest / "replay.json").write_text(json.dumps(replay), encoding="utf-8")
    assert replay["provenance"]["max_position_error_m"] == 0
    assert replay["provenance"]["missing_source_frames"] == 0
    frames = {f["observation_seq"]: f for f in replay["frames"]}
    calls = [read(p) for p in sorted((root / "debug/calls").glob("*.json"))]
    images = []
    for call in calls:
        assert call["model_id"] == "qwen3-vl:4b" and len(call["image_files"]) == 1
        frame = frames[call["observation_seq"]]
        rgb = Image.open(io.BytesIO(base64.b64decode(frame["rgb"].split(",")[1]))).convert("RGB")
        original = Image.open(root / call["image_files"][0]).convert("RGB")
        assert np.array_equal(np.asarray(rgb), np.asarray(original)), call["id"]
        images.append(dict(call=call["id"], role=call["role"], status=call["status"]))
    es = events(root)
    controls = [e for e in es if e["event_type"] == "control"]
    source = {
        e["trace_id"]: e
        for e in es
        if e["event_type"] == "decision_proposed" and "source_observation_seq" in e["payload"]
    }
    plans = [
        e
        for e in es
        if e["event_type"] == "plan"
        and "target_commitment_source_id" in e["payload"].get("planner_metadata", {})
    ]
    leases = {}
    for e in plans:
        m = e["payload"]["planner_metadata"]
        owner = m["target_commitment_source_id"]
        p = source[owner]["payload"]
        source_t = source[owner]["t_sim_ns"] - round(p["production_latency_s"] * 1e9)
        assert int(m["target_commitment_source_t_ns"]) == source_t
        assert int(m["target_commitment_source_seq"]) == p["source_observation_seq"]
        assert p["provenance"]["waypoint_kind"] == "target"
        deadline = int(m["target_commitment_deadline_ns"]) / 1e9
        if owner in leases:
            assert leases[owner]["deadline_s"] == deadline
        else:
            leases[owner] = dict(
                activation_s=deadline - 20,
                deadline_s=deadline,
                source_t_s=source_t / 1e9,
                source_seq=p["source_observation_seq"],
            )
    old = 0
    stale_zero_holds = 0
    excess = []
    for e in controls:
        p = e["payload"]
        age = p.get("decision_age_s")
        t = e["t_sim_ns"] / 1e9
        speed = float(np.linalg.norm([p[k] for k in ["vx", "vy", "vz"]]))
        if speed > 0.6:
            excess.append(speed - 0.6)
        if age is not None and age > 4 + 1e-8:
            if e["trace_id"] is None:
                assert p["source_observation_seq"] is None
                assert all(p[k] == 0 for k in ["vx", "vy", "vz", "yaw_rate"])
                stale_zero_holds += 1
                continue
            old += 1
            lease = leases[e["trace_id"]]
            assert lease["activation_s"] <= t < lease["deadline_s"]
            assert abs(age - (t - lease["source_t_s"])) < 1e-8
            assert p["source_observation_seq"] == lease["source_seq"]
    final = replay["frames"][-1]
    proof = dict(
        name=name,
        result=read(root / "result.json"),
        provenance=replay["provenance"],
        source_images=len(images),
        image_roles=dict(Counter(r["role"] for r in images)),
        model_calls=dict(Counter(c["status"] for c in calls)),
        leases=leases,
        old_source_commands=old,
        stale_zero_holds=stale_zero_holds,
        raw_speed_violations=len(excess),
        max_speed_excess_mps=max(excess, default=0),
        closest_m=min(f["distance"] for f in replay["frames"]),
        closest_s=min(replay["frames"], key=lambda f: f["distance"])["t"],
        final_speed_mps=math.sqrt(sum(v * v for v in final["velocity"])),
        monitor_labels=dict(
            Counter(e["payload"]["label"] for e in es if e["event_type"] == "monitor")
        ),
    )
    (dest / "AUDIT.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    (dest / "events.jsonl.gz").write_bytes(
        gzip.compress((root / "events.jsonl").read_bytes(), mtime=0)
    )
    for filename in ["manifest.json", "result.json"]:
        shutil.copy2(root / filename, dest / filename)
    shutil.copytree(root / "debug", dest / "debug", dirs_exist_ok=True)
    (dest / "replay.json").write_text(json.dumps(replay), encoding="utf-8")
    page = html_document(dict(schema=1, runs=[replay], sources=_sources()))
    Path(f"reports/debugger/{PAGE}_{variant}.html").write_text(page, encoding="utf-8")
    print(
        json.dumps(
            {
                k: proof[k]
                for k in ["name", "source_images", "model_calls", "closest_m", "closest_s"]
            }
        )
    )


def compare():
    runs = [read(OUT / v / "replay.json") for v in ["off", "on"]]
    roots = [Path("runs") / r["name"] for r in runs]
    all_events = [events(r) for r in roots]
    controls = [[e for e in es if e["event_type"] == "control"] for es in all_events]
    first = None
    keys = ["position_x", "position_y", "position_z", "vx", "vy", "vz", "yaw_rate"]
    for a, b in zip(*controls, strict=False):
        if a["t_sim_ns"] != b["t_sim_ns"] or any(a["payload"][k] != b["payload"][k] for k in keys):
            first = b["t_sim_ns"] / 1e9
            break
    calls = [[read(p) for p in sorted((r / "debug/calls").glob("*.json"))] for r in roots]
    indexes = [{(c["role"], c["started_t_sim_ns"]): c for c in cs} for cs in calls]
    common = []
    for key, a in indexes[0].items():
        b = indexes[1].get(key)
        if not b or a["status"] != "complete" or b["status"] != "complete":
            continue
        same_image = (roots[0] / a["image_files"][0]).read_bytes() == (
            roots[1] / b["image_files"][0]
        ).read_bytes()
        same_input = (
            same_image
            and a["prompt"] == b["prompt"]
            and a["response_schema"] == b["response_schema"]
        )
        common.append(
            dict(
                role=key[0],
                t=key[1] / 1e9,
                same_input=same_input,
                same_response=a["response"] == b["response"],
                off_response=a["response"]
                if same_input and a["response"] != b["response"]
                else None,
                on_response=b["response"]
                if same_input and a["response"] != b["response"]
                else None,
            )
        )
    on = read(OUT / "on/AUDIT.json")
    first_lease = min((x["activation_s"] for x in on["leases"].values()), default=None)
    proof = dict(
        first_different_control_s=first,
        first_commitment_activation_s=first_lease,
        common_requests=common,
        caveat="Single development-seed pair, fixed order off/on. Matched configuration and "
        "GPU placement do not guarantee deterministic model outputs or reliability.",
    )
    (OUT / "COMPARISON.json").write_text(json.dumps(proof, indent=2), encoding="utf-8")
    page = html_document(dict(schema=1, runs=runs, sources=_sources()))
    page = page.replace(
        "run.result.success?'Completed':run.result.termination_reason",
        "run.result.success?'Completed':"
        "(run.result.termination_detail?.startsWith('diagnostic early stop')?"
        "'Diagnostic stop (censored)':run.result.termination_reason)",
    )
    banner = (
        '<div style="padding:12px 24px;background:#18303d;color:#e3f5ff">'
        "Fresh GPU flights, same seed and 240 s limit. "
        "Only target commitment differs (off / 20 s). Single development comparison.</div>"
    )
    Path(f"reports/debugger/{PAGE}_comparison.html").write_text(
        page.replace("<body>", "<body>" + banner, 1), encoding="utf-8"
    )
    print(json.dumps(dict(first_control_difference=first, first_lease=first_lease)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("variant", choices=["off", "on", "compare"])
    parser.add_argument("--out", default=str(OUT))
    parser.add_argument("--page", default=PAGE)
    args = parser.parse_args()
    OUT = Path(args.out)
    PAGE = args.page
    if args.variant == "compare":
        compare()
    else:
        asyncio.run(one(args.variant))
