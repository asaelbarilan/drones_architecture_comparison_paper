"""Screen the unchanged shared-Qwen runtime on all nine existing capability tasks."""

import argparse
import asyncio
import hashlib
import json
import math
import threading
from collections import Counter
from pathlib import Path

from gpu_trace import GpuTrace
from run_qwen_async import deadline_exit
from run_qwen_full_architecture import experiment, provenance

from uavlab.adapters.gym.capability_env import SCENARIOS, CapabilityEnv
from uavlab.contracts import MissionSpec
from uavlab.core.compose import load_environment
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.control import LiveControl
from uavlab.live_qwen.evidence import Evidence
from uavlab.live_qwen.grounding import GROUNDING, VISUAL_PLANNER
from uavlab.live_qwen.latency import diagnostic_request, qualify
from uavlab.live_qwen.planner_memory import RECOVERY
from uavlab.live_qwen.prompts import DIRECTION, MONITOR, PLANNER
from uavlab.live_qwen.runner import flight_loop
from uavlab.live_qwen.scheduler import GoalScheduler
from uavlab.live_qwen.visual_progress import VISUAL_MONITOR


def finite_json(value):
    if isinstance(value, dict):
        return {key: finite_json(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [finite_json(item) for item in value]
    return None if isinstance(value, float) and not math.isfinite(value) else value


def task_binding(name, settings):
    config = load_environment("capability_" + name)
    mission = MissionSpec(mission_id=name, instruction=config.instruction,
                          task_family=config.task_family, success=config.params["success"],
                          constraints=config.params["constraints"])
    bound = dict(settings, flight_seconds=config.max_episode_s,
                 goal_mode="numeric" if name == "known_goal" else "visual")
    bound.update(config.params["constraints"])
    return config, mission, bound


def task_pass(status, mission, stopped):
    """Mirror orchestrator._succeeded, keeping runtime health separate."""
    if status.collided or status.out_of_bounds:
        return False
    if status.subgoals_total and status.subgoals_completed < mission.success.required_subgoals:
        return False
    complete = status.within_goal if status.task_complete is None else status.task_complete
    return bool(complete and (stopped or not mission.success.require_terminal_stop))


def score(state, evidence, gaps, status):
    actions = [r for r in evidence.events if r["kind"] == "action_consumed"]
    fresh = all(r["packet"]["ready_ns"] <= r["wall_ns"] < r["packet"]["expires_ns"]
                and r["until_ns"] <= r["packet"]["expires_ns"] for r in actions)
    return dict(task=state.mission.mission_id,
                task_pass=task_pass(status, state.mission, state.stopped),
                stopped=state.stopped, contract_failed=state.failed,
                status=finite_json(status.model_dump(mode="json")),
                fresh_actions=fresh, actions_consumed=len(actions),
                max_tick_gap_s=max(gaps, default=0),
                timing_pass=max(gaps, default=0) <= state.settings["max_tick_gap_s"],
                role_calls=dict(Counter(r["role"] for r in evidence.events
                                        if r["kind"] == "submitted")))


async def capability_flight(worker, case, settings, out):
    config, mission, bound = task_binding(case["id"], settings)
    evidence = Evidence(out)
    env = CapabilityEnv(**config.params)
    state = GoalScheduler(worker, mission, bound, evidence)
    state.next_id = worker.last_id+1
    control = LiveControl(state, bound, case["seed"])
    print(f"START {case['id']} seed={case['seed']} limit={bound['flight_seconds']}s", flush=True)
    try:
        obs = await env.reset(mission, case["seed"])
        evidence.save("mission.json", mission.model_dump(mode="json"))
        evidence.save("initial_evaluator_only.json", finite_json(env.debug_scene()))
        global_store().get(obs.rgb.uri).save(out / "initial_camera.png")
        await qualify(worker, diagnostic_request(obs, bound), bound, evidence)
        state.next_id = worker.last_id+1
        obs, gaps = await flight_loop(env, control, obs, evidence)
        result = score(state, evidence, gaps, env.status())
        global_store().get(obs.rgb.uri).save(out / "final_camera.png")
        evidence.save("final_evaluator_only.json", finite_json(env.debug_scene()))
        evidence.save("result.json", result)
        return result
    except Exception as exc:
        evidence.save("failure.json", dict(error=repr(exc)))
        raise
    finally:
        worker.revoke()
        await env.close()
        evidence.close()


def prepare(out, seed):
    out.mkdir(parents=True, exist_ok=False)
    settings = json.loads(Path("configs/experiments/qwen_visual_object.json").read_text())
    settings.update(watchdog_s=1200, missions=[dict(id=name, seed=seed) for name in SCENARIOS])
    resolved = {name: task_binding(name, settings)[0].model_dump(mode="json") for name in SCENARIOS}
    prompts = dict(planner=PLANNER, direction=DIRECTION, monitor=MONITOR,
                   visual_planner=VISUAL_PLANNER, grounding=GROUNDING,
                   visual_monitor=VISUAL_MONITOR, recovery=RECOVERY)
    for name, value in (("config", settings), ("resolved_tasks", resolved),
                        ("prompt_templates", prompts)):
        (out / f"{name}.json").write_text(json.dumps(value, indent=2), encoding="utf-8")
    provenance(out)
    paths = [Path(__file__), Path("src/uavlab/adapters/gym/capability_env.py")]
    paths += list(Path("configs/environments").glob("capability_*.yaml"))
    hashes = json.loads((out / "source_hashes.json").read_text())
    hashes.update({p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (out / "source_hashes.json").write_text(json.dumps(hashes, indent=2), encoding="utf-8")
    return settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1061)
    args = parser.parse_args()
    settings = prepare(args.out, args.seed)
    timer = threading.Timer(settings["watchdog_s"], deadline_exit)
    timer.daemon = True
    timer.start()
    try:
        with GpuTrace(args.out):
            asyncio.run(experiment(settings, args.out, capability_flight))
    except Exception as exc:
        (args.out / "failure.json").write_text(json.dumps(dict(error=repr(exc))))
        raise
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
