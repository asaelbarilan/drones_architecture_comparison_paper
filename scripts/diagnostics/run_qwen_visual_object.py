"""Real shared model object-approach probe; hidden truth is evaluator-only."""

import argparse
import asyncio
import hashlib
import json
import threading
from collections import Counter
from pathlib import Path

from run_qwen_async import deadline_exit
from run_qwen_full_architecture import experiment, provenance

from uavlab.core.frame_store import global_store
from uavlab.core.registry import REGISTRY
from uavlab.live_qwen.control import LiveControl
from uavlab.live_qwen.evidence import Evidence
from uavlab.live_qwen.latency import diagnostic_request, qualify
from uavlab.live_qwen.prompts import DIRECTION, MONITOR, PLANNER
from uavlab.live_qwen.runner import flight_loop, mission_spec
from uavlab.live_qwen.scheduler import GoalScheduler


def score(state, obs, evidence, gaps, status):
    actions = [r for r in evidence.events if r["kind"] == "action_consumed"]
    fresh = all(r["wall_ns"] < r["packet"]["expires_ns"]
                and r["until_ns"] <= r["packet"]["expires_ns"] for r in actions)
    accepted = (state.stopped and status.goal_visible
                and status.distance_to_goal_m <= state.settings["audit_criteria"]["near_object_m"]
                and obs.velocity.norm() <= state.settings["stopped_mps"])
    safe = not status.collided and not status.out_of_bounds and fresh
    return dict(task_pass=accepted and safe, stopped=state.stopped, contract_failed=state.failed,
                distance_to_object_m=status.distance_to_goal_m, object_visible=status.goal_visible,
                final_speed_mps=obs.velocity.norm(), collisions=status.collision_count,
                out_of_bounds=status.out_of_bounds, fresh_actions=fresh,
                actions_consumed=len(actions), max_tick_gap_s=max(gaps, default=0),
                timing_pass=max(gaps, default=0) <= state.settings["max_tick_gap_s"],
                role_calls=dict(Counter(r["role"] for r in evidence.events
                                        if r["kind"] == "submitted")),
                scope="visible red pillar in rendered grid3d, not AirSim/search/general cognition")


async def visual_flight(worker, case, settings, out):
    evidence = Evidence(out)
    env = REGISTRY.build("environment", **settings["environment"])
    state = GoalScheduler(worker, mission_spec(case, settings), settings, evidence)
    control = LiveControl(state, settings, case["seed"])
    try:
        obs = await env.reset(state.mission, case["seed"])
        truth = dict(object_position=env.goal.tolist(), start=obs.position.model_dump(),
                     initial_distance_m=env.status().distance_to_goal_m)
        evidence.save("evaluator_only.json", truth)
        global_store().get(obs.rgb.uri).save(out / "initial_camera.png")
        await qualify(worker, diagnostic_request(obs, settings), settings, evidence)
        state.next_id = worker.last_id+1
        obs, gaps = await flight_loop(env, control, obs, evidence)
        result = score(state, obs, evidence, gaps, env.status())
        global_store().get(obs.rgb.uri).save(out / "final_camera.png")
        evidence.save("result.json", result)
        return result
    except Exception as exc:
        evidence.save("failure.json", dict(error=repr(exc)))
        raise
    finally:
        worker.revoke()
        await env.close()
        evidence.close()


def prepare(config, out):
    out.mkdir(parents=True, exist_ok=False)
    settings = json.loads(config.read_text())
    (out / "config.json").write_text(json.dumps(settings, indent=2))
    (out / "prompt_templates.json").write_text(json.dumps(
        dict(planner=PLANNER, direction=DIRECTION, monitor=MONITOR), indent=2))
    provenance(out)
    hashes = json.loads((out / "source_hashes.json").read_text())
    hashes[Path(__file__).name] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (out / "source_hashes.json").write_text(json.dumps(hashes, indent=2))
    return settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    settings = prepare(args.config, args.out)
    timer = threading.Timer(settings["watchdog_s"], deadline_exit)
    timer.daemon = True
    timer.start()
    try:
        asyncio.run(experiment(settings, args.out, visual_flight))
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
