"""Paper architecture switches (D-160): one model, one wall-clock runtime, many architectures.

Each paper configuration (C0, C2-C6, C10, C13 ...) is a set of these switches over the same
GoalScheduler, the same shared Qwen3-VL-4B worker, controller, shield and tasks. The defaults
reproduce the D-158 full stack exactly, so every earlier config keeps its behaviour.

  goal_source  planned     the model plans ordered steps from the mission (default)
               instruction no planner call: the mission text is the single step
               oracle      privileged final goal from the evaluator (C0 ceiling only)
               skills      a text-only LLM agent picks one skill per turn (C1, skills.py)
  verifier     True        reject goals that change committed steps or leave the envelope
  monitor      default     arrival/near checks plus periodic checks on numeric legs
               periodic    also periodic checks on visual legs
               none        no monitor: arrival / fresh near grounding completes a step
  recovery     event       stall / target loss / monitor replan wake the recovery planner
               periodic    also wake it every recovery_interval_s (C10)
               none        no recovery planner: the same step is simply retried
  memory       True        planner event memory and object position memory
"""

import json
import math

from .world_contract import explicit_world

DEFAULTS = dict(goal_source="planned", verifier=True, monitor="default", recovery="event",
                memory=True, recovery_interval_s=20.0)
CHOICES = dict(goal_source={"planned", "instruction", "oracle", "skills"},
               monitor={"default", "periodic", "none"},
               recovery={"event", "periodic", "none"})


def switches(settings):
    """Merged, validated switches; unknown keys or values fail before any flight."""
    given = settings.get("architecture") or {}
    unknown = set(given) - set(DEFAULTS) - {"name"}
    if unknown:
        raise ValueError(f"unknown architecture switches: {sorted(unknown)}")
    merged = dict(DEFAULTS, **given)
    for key, allowed in CHOICES.items():
        if merged[key] not in allowed:
            raise ValueError(f"architecture {key} must be one of {sorted(allowed)}")
    for key in ("verifier", "memory"):
        if type(merged[key]) is not bool:
            raise ValueError(f"architecture {key} must be true or false")
    return merged


def switch(settings, key):
    return switches(settings)[key]


def unplanned_steps(state):
    """Steps without a planner call: explicit public coordinates, else the whole mission."""
    instruction = state.mission.instruction
    if switch(state.settings, "goal_source") == "oracle":
        return [dict(objective=instruction, target=dict(world_enu=oracle_point(state)))]
    world = explicit_world(instruction)
    if world is not None and state.settings.get("goal_mode") != "visual":
        return [dict(objective=instruction, target=dict(world_enu=world))]
    return [dict(objective=instruction, target=instruction)]


def oracle_point(state):
    """C0: the evaluator's goal, approached to a standoff on visual tasks (privileged)."""
    goal = state.settings.get("oracle_goal")
    if goal is None:
        raise ValueError("oracle goal_source needs the evaluator goal (C0 only)")
    start = state.origin.position
    if state.settings.get("oracle_visual"):
        dx, dy = goal[0] - start.x, goal[1] - start.y
        distance = math.hypot(dx, dy)
        standoff = state.settings.get("oracle_standoff_m", 1.0)
        keep = max(0.0, distance - standoff) / max(distance, 1e-9)
        return [start.x + dx * keep, start.y + dy * keep, start.z]
    return [float(v) for v in goal]


def commit_unplanned(state, now):
    """Commit the planner-free mission once, as accept_plan would; oracle also gets its goal."""
    state.steps = unplanned_steps(state)
    state.plan = dict(state.steps[0])
    state.log("mission_plan_committed", now, mission=state.mission.instruction, authored=None,
              steps=state.steps, step_index=0, goal_source=switch(state.settings, "goal_source"))
    if switch(state.settings, "goal_source") == "oracle":
        payload = dict(kind="world", target=state.plan["target"], terminal=True)
        state.accept_goal(payload, state.origin, now, now)


def no_monitor(state, reason, now):
    """Monitor-free completion: arrival or fresh near grounding ends the step directly."""
    state.pause(reason, now)
    settled = state.last_obs.velocity.norm() <= state.settings["stopped_mps"]
    if state.settings.get("goal_mode") != "visual":
        arrived = state.goal is not None and state.goal.arrived(state.last_obs, state.settings)
        if arrived and settled:
            state.finish_step(now)
        return
    state.visual_stop_pending = reason.startswith("fresh object proximity")
    state.replan(reason, now)


def recovery_due(state, now):
    interval = switch(state.settings, "recovery_interval_s") * 1e9
    return (switch(state.settings, "recovery") == "periodic" and bool(state.steps)
            and now - state.last_recovery >= interval)


def bounded(position, settings):
    """The verifier's envelope check (altitude band and geofence)."""
    if not settings["min_altitude_m"] <= position.z <= settings["max_altitude_m"]:
        raise ValueError("goal outside altitude envelope")
    if math.hypot(position.x, position.y) > settings["geofence_radius_m"]:
        raise ValueError("goal outside geofence")


def unverified_direction(state, payload):
    """Without a verifier the direction is used as given; the scheduler still owns step order."""
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    last = not state.steps or state.step_index == len(state.steps) - 1
    return dict(data, terminal=data.get("terminal", last) and last)
