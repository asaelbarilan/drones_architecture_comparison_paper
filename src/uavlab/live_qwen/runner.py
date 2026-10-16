"""Reusable wall-clock runner over the repository's EnvironmentAdapter contract."""

import asyncio
import time

from uavlab.contracts import MissionConstraints, MissionSpec, TaskFamily, Vec3, s_to_ns
from uavlab.core.registry import REGISTRY
from uavlab.plugins.inference.qwen_worker import QwenWorker

from .control import LiveControl, context
from .evidence import Evidence, summarize
from .latency import diagnostic_request, qualify
from .scheduler import GoalScheduler

PHYSICS_STEP_NS = s_to_ns(0.05)


async def advance(env, command, sim_ns, duration_ns):
    """Honor expiration even if the parent misses a tick; never replay stale thrust."""
    remaining = duration_ns
    while remaining > 0:
        step = min(remaining, PHYSICS_STEP_NS)
        expiry = command.expires_t_sim_ns
        if expiry is not None and sim_ns < expiry:
            step = min(step, expiry-sim_ns)
        if expiry is not None and sim_ns >= expiry:
            command = command.model_copy(update=dict(velocity=Vec3(x=0, y=0, z=0), yaw_rate_rps=0))
        await env.step(command, step)
        sim_ns += step
        remaining -= step


def mission_spec(case, settings):
    constraints = {k: settings[k] for k in
                   ("max_speed_mps", "min_altitude_m", "max_altitude_m", "geofence_radius_m")}
    return MissionSpec(mission_id=case["id"], instruction=case["instruction"],
                       task_family=TaskFamily.LONG_HORIZON_NAV,
                       constraints=MissionConstraints(**constraints))


async def await_worker(worker, settings, ready=False):
    deadline = time.perf_counter()+settings["worker_ready_timeout_s"]
    while time.perf_counter() < deadline:
        for event in worker.poll(-1):
            if event["kind"] == "fatal":
                raise RuntimeError(event["payload"])
        if (worker.ready if ready else worker.current is None):
            return
        await asyncio.sleep(1/settings["control_hz"])
    raise TimeoutError("GPU worker readiness/drain deadline")


async def fly(worker, case, settings, out):
    evidence = Evidence(out)
    env = REGISTRY.build("environment", **settings["environment"])
    state = GoalScheduler(worker, mission_spec(case, settings), settings, evidence)
    state.next_id = worker.last_id+1
    control = LiveControl(state, settings, case["seed"])
    try:
        obs = await env.reset(state.mission, case["seed"])
        if settings.get("latency_preflight", True):
            request = diagnostic_request(obs, settings)
            await qualify(worker, request, settings, evidence)
            state.next_id = worker.last_id+1
        obs, gaps = await flight_loop(env, control, obs, evidence)
        result = summarize(state, obs, case, evidence, gaps)
        status = env.status()  # Scoring truth never enters state or model prompts.
        result.update(collisions=status.collision_count, out_of_bounds=status.out_of_bounds)
        evidence.save("result.json", result)
        return result
    except Exception as exc:
        evidence.save("failure.json", dict(error=f"{type(exc).__name__}: {exc}"))
        raise
    finally:
        worker.revoke()
        await env.close()
        evidence.close()


async def flight_loop(env, control, obs, evidence):
    settings, state = control.settings, control.scheduler
    period = 1/settings["control_hz"]
    start = last = time.perf_counter_ns()
    command = control.controller.hold(context(state.mission, obs, start))
    gaps = []
    while time.perf_counter_ns()-start < s_to_ns(settings["flight_seconds"]):
        wait = max(0, (last+s_to_ns(period)-time.perf_counter_ns())/1e9)
        await asyncio.to_thread(time.sleep, wait)
        now = time.perf_counter_ns()
        elapsed = now-last
        await advance(env, command, obs.t_sim_ns, elapsed)
        captured = time.perf_counter_ns()
        obs = await env.observe()
        command = control.tick(obs, captured, time.perf_counter_ns())
        gaps.append(elapsed/1e9)
        evidence(dict(kind="tick", wall_ns=now, sim_ns=obs.t_sim_ns, seq=obs.seq,
                      position=obs.position.model_dump(), yaw=obs.yaw_rad,
                      velocity=obs.velocity.model_dump(), command=command.model_dump(mode="json")))
        last = now
        status = env.status()
        if state.stopped or state.failed or status.collided or status.out_of_bounds:
            break
    state.pause("episode ended", time.perf_counter_ns())
    return obs, gaps


async def run_suite(settings, out):
    worker = QwenWorker(dict(package_path=settings["package_path"],
                             model_id=settings["model_id"], max_new_tokens=128,
                             cpu_placement=settings.get("cpu_placement", "inherit")))
    worker.start()
    results = {}
    try:
        await await_worker(worker, settings, ready=True)
        for case in settings["missions"]:
            results[case["id"]] = await fly(worker, case, settings, out / case["id"])
            await await_worker(worker, settings)
        return results
    finally:
        worker.close()
