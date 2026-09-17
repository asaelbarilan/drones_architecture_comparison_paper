"""Reconstruct depth at model-localized pixels; diagnostic only, no control changes."""

import asyncio
import json
from pathlib import Path

import numpy as np
from PIL import Image

from uavlab.adapters.gym.capability_env import CapabilityEnv
from uavlab.contracts import ControlCommand, MissionSpec, Vec3
from uavlab.core.camera import Camera
from uavlab.core.frame_store import global_store

ROOT = Path("runs/c2_visible_preflight_20260916_s1061")
OUT = Path("reports/spf_stop_contract_20260917")


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


async def main():
    freeze = read(OUT / "FREEZE.json")
    cfg = read(ROOT / "manifest.json")["environment_config"]
    mission = MissionSpec(
        mission_id="saved-spf-depth",
        instruction=cfg["instruction"],
        task_family=cfg["task_family"],
        success=cfg["params"]["success"],
        constraints=cfg["params"]["constraints"],
        allowed_skills=cfg["params"]["allowed_skills"],
    )
    sources = {
        c["source_call"]["observation_seq"]: c for c in freeze["cases"] if c["id"] != "green"
    }
    replies = {
        c["task"]["case"]: c["answer"]
        for path in (OUT / "calls").glob("*.json")
        if (c := read(path))["task"]["variant"] == "bbox"
    }
    controls = [
        json.loads(line)
        for line in (ROOT / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if json.loads(line)["event_type"] == "control"
    ]
    env = CapabilityEnv(**cfg["params"])
    await env.reset(mission, 1061)
    rows = []
    poses = 0
    for e in controls:
        obs = await env.observe()
        p = e["payload"]
        if obs.t_sim_ns / 1e9 > 40:
            break
        position = np.array([obs.position.x, obs.position.y, obs.position.z])
        assert np.linalg.norm(position - [p[f"position_{a}"] for a in "xyz"]) < 1e-8
        poses += 1
        if obs.seq in sources:
            c = sources[obs.seq]
            answer = replies[c["id"]]
            actual = np.asarray(global_store().get(obs.rgb.uri))
            assert np.array_equal(actual, np.asarray(Image.open(OUT / c["image"]).convert("RGB")))
            row = dict(
                case=c["id"],
                seq=obs.seq,
                t=obs.t_sim_ns / 1e9,
                model_visible=answer["visible"],
                metric_range_m=None,
                within_2m=False,
                diagnostic_true_center_range_m=c["source_distance_m"],
            )
            if answer["visible"]:
                b = answer["box"]
                u = (b[0] + b[2]) / 2 * (obs.intrinsics.width - 1) / 999
                v = (b[1] + b[3]) / 2 * (obs.intrinsics.height - 1) / 999
                depth = np.asarray(global_store().get(obs.depth.uri))
                d = float(depth[round(v), round(u)])
                camera = Camera(
                    width=obs.intrinsics.width,
                    height=obs.intrinsics.height,
                    fov_deg=cfg["params"]["fov_deg"],
                    pitch_rad=cfg["params"]["camera_pitch_rad"],
                )
                point = camera.unproject(u, v, d, position, obs.yaw_rad)
                distance = float(np.linalg.norm(point - position))
                row.update(
                    pixel=[u, v],
                    camera_forward_depth_m=d,
                    world_point=point.tolist(),
                    metric_range_m=distance,
                    within_2m=distance <= 2,
                )
            rows.append(row)
        await env.step(
            ControlCommand(
                t_sim_ns=e["t_sim_ns"],
                velocity=Vec3(x=p["vx"], y=p["vy"], z=p["vz"]),
                yaw_rate_rps=p["yaw_rate"],
            ),
            50_000_000,
        )
    await env.close()
    indexed = {r["case"]: r for r in rows}
    assert not indexed["far"]["within_2m"] and not indexed["width_threshold"]["within_2m"]
    assert indexed["close24"]["within_2m"] and indexed["close25"]["within_2m"]
    separation = float(
        np.linalg.norm(
            np.array(indexed["close24"]["world_point"]) - indexed["close25"]["world_point"]
        )
    )
    result = dict(
        poses_checked=poses,
        source_images_checked=len(rows),
        rows=rows,
        close_target_point_separation_m=separation,
        scope=(
            "Diagnostic geometry feasibility on recorded states; not a deployed stop policy, "
            "new flight or proof of closed-loop success. "
            "Source target-center truth used only for evaluation."
        ),
    )
    (OUT / "DEPTH_CHECK.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
