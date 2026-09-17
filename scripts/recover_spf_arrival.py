"""Recover the interrupted D-129 evidence without altering the original run."""

import asyncio
import base64
import gzip
import io
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

from uavlab.adapters.gym.capability_env import CapabilityEnv
from uavlab.analysis.flight_debugger import _sources, html_document, load_run
from uavlab.contracts import ControlCommand, MissionSpec, Vec3

SRC = Path("runs/c2_spf_arrival_20260917_s1061")
OUT = Path("reports/spf_arrival_20260917")
DEST = OUT / "interrupted_c2"


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


async def main():
    manifest = read(SRC / "manifest.json")
    cfg = manifest["environment_config"]
    mission = MissionSpec(
        mission_id="recover-interrupted",
        instruction=cfg["instruction"],
        task_family=cfg["task_family"],
        success=cfg["params"]["success"],
        constraints=cfg["params"]["constraints"],
        allowed_skills=cfg["params"]["allowed_skills"],
    )
    es = [json.loads(s) for s in (SRC / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    end = next(e for e in reversed(es) if e["event_type"] == "episode_end")
    env = CapabilityEnv(**cfg["params"])
    await env.reset(mission, 1061)
    checks = 0
    for e in es:
        if e["event_type"] != "control":
            continue
        obs = await env.observe()
        p = e["payload"]
        assert obs.t_sim_ns == e["t_sim_ns"]
        assert (
            np.linalg.norm(np.array(obs.position.as_tuple()) - [p[f"position_{a}"] for a in "xyz"])
            < 1e-8
        )
        checks += 1
        await env.step(
            ControlCommand(
                t_sim_ns=e["t_sim_ns"],
                velocity=Vec3(x=p["vx"], y=p["vy"], z=p["vz"]),
                yaw_rate_rps=p["yaw_rate"],
            ),
            50_000_000,
        )
    status = env.status()
    await env.close()
    # This is explicitly a recovered debugger summary, NOT the lost original result.
    result = dict(
        episode_id=SRC.name,
        architecture_id=manifest["architecture_config"]["id"],
        environment_id=cfg["id"],
        seed=1061,
        success=end["payload"]["success"],
        termination_reason=end["payload"]["reason"],
        termination_detail=end["payload"]["detail"],
        sim_duration_s=end["payload"]["sim_duration_s"],
        metrics={"distance_to_goal_m": status.distance_to_goal_m},
        status=status.model_dump(mode="json"),
        recovery_provenance=(
            "Original result.json was never written after optional Parquet OOM. "
            "Termination copied from episode_end; metric/status reconstructed from exact "
            "logged controls. Not an independent final-status match."
        ),
    )
    DEST.mkdir(parents=True, exist_ok=True)
    for name in ["manifest.json", "events.jsonl"]:
        shutil.copy2(SRC / name, DEST / name)
    shutil.copytree(SRC / "debug", DEST / "debug", dirs_exist_ok=True)
    (DEST / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    replay = await load_run(DEST)
    replay["name"] = SRC.name
    replay["provenance"]["final_status_reconstructed"] = True
    frames = {f["observation_seq"]: f for f in replay["frames"]}
    calls = [read(p) for p in sorted((SRC / "debug/calls").glob("*.json"))]
    for c in calls:
        actual = Image.open(SRC / c["image_files"][0]).convert("RGB")
        rebuilt = Image.open(
            io.BytesIO(base64.b64decode(frames[c["observation_seq"]]["rgb"].split(",")[1]))
        ).convert("RGB")
        assert np.array_equal(np.asarray(actual), np.asarray(rebuilt))
    audit = dict(
        control_poses_checked=checks,
        source_images_checked=len(calls),
        nonempty_replies=sum(bool(c.get("response")) for c in calls),
        empty_replies=sum(not c.get("response") for c in calls),
        final_distance_reconstructed_m=status.distance_to_goal_m,
        stopped=False,
        arrival_validated=False,
        final_status_independent_check=False,
    )
    (DEST / "AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (DEST / "events.jsonl.gz").write_bytes(
        gzip.compress((SRC / "events.jsonl").read_bytes(), mtime=0)
    )
    (DEST / "replay.json").write_text(json.dumps(replay), encoding="utf-8")
    page = html_document(dict(schema=1, runs=[replay], sources=_sources()))
    banner = (
        '<div style="padding:18px;background:#502b22;color:white">'
        "D-129 INTERRUPTED: local inference memory failure at31s; no arrival verdict. "
        "Original result export also failed. Termination comes from the saved event; "
        "final metric/status are reconstructed from logged controls. C3 has not run.</div>"
    )
    Path("reports/debugger/spf_arrival.html").write_text(
        page.replace("<body>", "<body>" + banner, 1), encoding="utf-8"
    )
    print(json.dumps(audit))


if __name__ == "__main__":
    asyncio.run(main())
