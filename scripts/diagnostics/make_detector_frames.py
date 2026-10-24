"""D-186 detector probe, step 1: camera frames with true object boxes from the simulator.

For each object task and development seed, the drone is placed at the start pose and at 3 m
and 6 m along the line to the object (facing it); the rendered RGB is saved with the true box
of every visible object (oracles.true_box: only the visible part, never a hidden object).
Step 2 (probe_detectors.py) runs open-vocabulary detectors on these frames. Offline only.

    python scripts/diagnostics/make_detector_frames.py --out reports/detector_probe
"""

import argparse
import asyncio
import json
import math
from pathlib import Path

import numpy as np

from uavlab.adapters.gym.capability_env import CapabilityEnv
from uavlab.contracts import MissionSpec
from uavlab.core.compose import load_environment
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.oracles import scene_objects, true_box

TASKS = ("visible_target", "approach_hover", "ordered_visit", "overturned_vehicle",
         "obstacle_low_wall", "conditional_gate")
SEEDS = (1060, 1061, 1062)
ADVANCE_M = (0.0, 3.0, 6.0)
SETTINGS = dict(camera_pitch_rad=-0.10)


def place(env, position, yaw):
    env.vehicle.position = np.asarray(position, dtype=float)
    env.vehicle.velocity = np.zeros(3)
    env.vehicle.yaw = yaw


async def frames_for(task, seed, out):
    config = load_environment("capability_" + task)
    mission = MissionSpec(mission_id=task, instruction=config.instruction,
                          task_family=config.task_family, success=config.params["success"],
                          constraints=config.params["constraints"])
    env = CapabilityEnv(**config.params)
    rows = []
    try:
        await env.reset(mission, seed)
        objects = scene_objects(env)
        target = np.asarray(env.debug_scene()["goal"], dtype=float)
        yaw = math.atan2(target[1], target[0])
        for advance in ADVANCE_M:
            place(env, (advance * math.cos(yaw), advance * math.sin(yaw), 3.0), yaw)
            obs = await env.observe()
            depth = np.asarray(global_store().get(obs.depth.uri))
            name = f"{task}_s{seed}_a{int(advance)}.png"
            global_store().get(obs.rgb.uri).save(out / name)
            boxes = {label: true_box((label, pos, size), obs, SETTINGS, depth)
                     for label, pos, size in objects}
            rows.append(dict(image=name, task=task, seed=seed, advance_m=advance,
                             boxes={k: v for k, v in boxes.items() if v is not None}))
    finally:
        await env.close()
    return rows


async def main_async(out):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for task in TASKS:
        for seed in SEEDS:
            rows += await frames_for(task, seed, out)
    (out / "truth.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    print(len(rows), "frames ->", out)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=Path("reports/detector_probe/frames"))
    asyncio.run(main_async(parser.parse_args().out))


if __name__ == "__main__":
    main()
