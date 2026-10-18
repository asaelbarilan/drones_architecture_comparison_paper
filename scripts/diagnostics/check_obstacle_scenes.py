"""Harness check for the D-156 obstacle scenes, before any flight.

For each scene: (1) the depth at the pillar's grounding pixel (box centre) must
be the pillar, not the obstacle, so grounding is unaffected; (2) the straight
line the visual waypoint follows must pass within the drone radius (collision)
or the shield's hard-stop distance of an obstacle, so a straight-line pilot
cannot finish without avoiding. Saves the initial camera image for inspection.
"""

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np

from uavlab.adapters.gym.capability_env import OBSTACLE_SCENARIOS, CapabilityEnv
from uavlab.contracts import MissionSpec
from uavlab.core.compose import load_environment
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.goals import visual_goal
from uavlab.live_qwen.grounding import COORD_MAX, observed_range

SHIELD_HARD_STOP_M = 1.0
STANDOFF_M = 1.25
RED_MIN, OTHER_MAX = 150, 90


def pillar_pixel(rgb):
    """Centre of the visible red region: what a correct grounding box returns.

    An occluder hides part of the pillar, so this differs from its true centre.
    """
    image = np.asarray(rgb.convert("RGB")).astype(int)
    red = (image[..., 0] > RED_MIN) & (image[..., 1] < OTHER_MAX) & (image[..., 2] < OTHER_MAX)
    rows, cols = np.nonzero(red)
    return int((cols.min() + cols.max()) // 2), int((rows.min() + rows.max()) // 2)


async def check(name, out):
    config = load_environment("capability_" + name)
    env = CapabilityEnv(**config.params)
    mission = MissionSpec(mission_id=name, instruction=config.instruction,
                          task_family=config.task_family, success=config.params["success"],
                          constraints=config.params["constraints"])
    obs = await env.reset(mission, 1061)
    rgb = global_store().get(obs.rgb.uri)
    rgb.save(out / f"{name}_initial.png")
    depth = np.asarray(global_store().get(obs.depth.uri))
    u, v = pillar_pixel(rgb)
    pixel_depth = float(depth[v, u])
    pillar_forward = float(env.goal[0] - env.vehicle.position[0])
    # The leg the runtime would issue: same grounding range and waypoint code.
    start = env.vehicle.position.copy()
    width, height = obs.intrinsics.width, obs.intrinsics.height
    box_u, box_v = u * COORD_MAX // width, v * COORD_MAX // height
    proposal = dict(target=dict(u=box_u, v=box_v))
    distance = observed_range(proposal, obs, depth)
    travel = min(10.0, max(0.6, distance - STANDOFF_M))
    goal, _ = visual_goal(dict(u=box_u, v=box_v, travel_m=travel, target_visible=True,
                               box=[box_u - 1, box_v - 1, box_u + 1, box_v + 1]),
                          obs, dict(camera_pitch_rad=-0.10, min_altitude_m=0.5, max_goal_m=10))
    end = np.array([goal.x, goal.y, goal.z])
    samples = start + np.linspace(0, 1, 400)[:, None] * (end - start)
    clearance = float(env._distance_to_obstacles(samples).min())
    result = dict(scene=name, pillar_pixel=[u, v], depth_at_pillar_pixel_m=round(pixel_depth, 3),
                  grounding_range_m=round(distance, 3),
                  pillar_forward_m=pillar_forward,
                  grounding_sees_pillar=abs(pixel_depth - pillar_forward) < 1.0,
                  straight_leg_min_clearance_m=round(clearance, 3),
                  drone_radius_m=env.drone_radius_m,
                  straight_leg_collides=clearance <= env.drone_radius_m,
                  straight_leg_blocked=clearance <= SHIELD_HARD_STOP_M,
                  leg_end=[round(float(x), 2) for x in end])
    await env.close()
    return result


async def main(out):
    out.mkdir(parents=True, exist_ok=True)
    results = [await check(name, out) for name in OBSTACLE_SCENARIOS]
    (out / "scene_checks.json").write_text(json.dumps(results, indent=1))
    for r in results:
        print(json.dumps(r))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    asyncio.run(main(parser.parse_args().out))
