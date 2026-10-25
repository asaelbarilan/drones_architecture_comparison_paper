"""Paper architecture switches (D-160): one model, one wall-clock runtime, many architectures.

Each paper configuration (C0, C2-C6, C10, C13 ...) is a set of these switches over the same
GoalScheduler, the same shared Qwen3-VL-4B worker, controller, shield and tasks. The defaults
reproduce the D-158 full stack exactly, so every earlier config keeps its behaviour.

  goal_source  planned     the model plans ordered steps from the mission (default)
               instruction no planner call: the mission text is the single step
               oracle      privileged final goal from the evaluator (C0 ceiling only)
               skills      a text-only LLM agent picks one skill per turn (C1, skills.py)
               vla_native  the D207 VLA writes its own box + Left line; the first line is
                           the goal (goal memory), as in its UAV-Flow server (C7/C8)
  verifier     True        reject goals that change committed steps or leave the envelope
  monitor      default     arrival/near checks plus periodic checks on numeric legs
               periodic    also periodic checks on visual legs
               none        no monitor: arrival / fresh near grounding completes a step
  recovery     event       stall / target loss / monitor replan wake the recovery planner
               periodic    also wake it every recovery_interval_s (C10)
               none        no recovery planner: the same step is simply retried
  memory       True        planner event memory and object position memory
  contract     flat        the planner writes plain objective/target steps (default)
               typed       H1: a typed program (visit/pass/condition/follow/goto/search)
  executive    basic       every step is fly-to-target-and-stop (default)
               kinds       H2: one owner executes the step kinds (executive.py)
  perception   vlm         objects and openings only from the VLM (default)
               openings    H5: measured range-fan openings for checks and pass steps
  tracking     stop        a follow step stops to look each time (default)
               moving      H7: a follow step looks again while flying (executive.py)
  detour       none        a hidden object starts the camera search (default)
               wall        H5 detour (D-177/178): aim behind a measured wall ahead, path progress
  search       planner     only a planner (recovery / H2) authorizes the camera search (default)
               policy      H3: a find / search mission starts it itself (connections.py)
  completion   default     planned steps read stated standoff / hold; memory keeps groundings
               evidence    H4: also for unplanned missions; measured legs look again
  measure      model       the VLA line's distance is used as written (default)
               range       H9: the VLA's own box gives the bearing, depth the distance
  oracle_plan  False       D-185 privileged: the first typed program is the correct one
  oracle_grounding False   D-185 privileged: looks return the true box of a visible object
                           (oracles.py; reference lines only, never results)
  oracle_delay_s 0.0       hold an oracle look for the model's measured grounding latency
  plan_check   none        the parsed typed program is executed as written (default)
               structure   H11: code checks it against the mission structure (plan_check.py)
  review       always      a periodic recovery review fires on its timer (default)
               idle        H8: it waits until the current step stops making progress
  output       strict      a direction answer must already have the runtime's format (default)
               lenient     H12: a bare world [x, y, z] list is wrapped as world_enu
"""

import dataclasses
import json
import math

from .mission_plan import add_stated_fields
from .world_contract import explicit_world

WORLD_CHANNELS = 3
DEFAULTS = dict(goal_source="planned", verifier=True, monitor="default", recovery="event",
                memory=True, recovery_interval_s=20.0, contract="flat", executive="basic",
                perception="vlm", tracking="stop", detour="none", search="planner",
                completion="default", measure="model", oracle_plan=False,
                oracle_grounding=False, oracle_delay_s=0.0, plan_check="none",
                review="always", output="strict")
CHOICES = dict(goal_source={"planned", "instruction", "oracle", "skills", "vla_native"},
               monitor={"default", "periodic", "none"},
               recovery={"event", "periodic", "none"},
               contract={"flat", "typed"}, executive={"basic", "kinds"},
               perception={"vlm", "openings"}, tracking={"stop", "moving"},
               detour={"none", "wall"}, search={"planner", "policy"},
               completion={"default", "evidence"}, measure={"model", "range"},
               plan_check={"none", "structure"}, review={"always", "idle"},
               output={"strict", "lenient"})


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
    for key in ("verifier", "memory", "oracle_plan", "oracle_grounding"):
        if type(merged[key]) is not bool:
            raise ValueError(f"architecture {key} must be true or false")
    return merged


def switch(settings, key):
    return switches(settings)[key]


def unplanned_steps(state):
    """Steps without a planner call; H4 reads their stated standoff / hold (connections.py)."""
    from .connections import stated_steps

    return stated_steps(state, mission_steps(state))


def mission_steps(state):
    """Explicit public coordinates, else the whole mission as one step."""
    instruction = state.mission.instruction
    if switch(state.settings, "goal_source") == "oracle":
        step = dict(objective=instruction)
        add_stated_fields(step)  # stated standoff / hold, read from public text as for all
        return [dict(step, target=dict(world_enu=oracle_point(state, step.get("standoff_m"))))]
    world = explicit_world(instruction)
    if world is not None and state.settings.get("goal_mode") != "visual":
        return [dict(objective=instruction, target=dict(world_enu=world))]
    return [dict(objective=instruction, target=instruction)]


def oracle_point(state, stated_standoff=None):
    """C0: the evaluator's goal, approached to a standoff on visual tasks (privileged)."""
    goal = state.settings.get("oracle_goal")
    if goal is None:
        raise ValueError("oracle goal_source needs the evaluator goal (C0 only)")
    start = state.origin.position
    if state.settings.get("oracle_visual"):
        dx, dy = goal[0] - start.x, goal[1] - start.y
        distance = math.hypot(dx, dy)
        standoff = stated_standoff or state.settings.get("oracle_standoff_m", 1.0)
        keep = max(0.0, distance - standoff) / max(distance, 1e-9)
        return [start.x + dx * keep, start.y + dy * keep, start.z]
    return [float(v) for v in goal]


def commit_unplanned(state, now):
    """Commit the planner-free mission once, as accept_plan would; oracle also gets its goal."""
    if switch(state.settings, "goal_source") == "vla_native":
        state.settings["goal_mode"] = "numeric"
        state.steps = [dict(objective=state.mission.instruction, target=[0, 0, 0, 0])]
    else:
        state.steps = unplanned_steps(state)
    state.plan = dict(state.steps[0])
    state.log("mission_plan_committed", now, mission=state.mission.instruction, authored=None,
              steps=state.steps, step_index=0, goal_source=switch(state.settings, "goal_source"))
    if switch(state.settings, "goal_source") == "oracle":
        payload = dict(kind="world", target=state.plan["target"], terminal=True)
        state.accept_goal(payload, state.origin, now, now)
        if state.settings.get("oracle_visual"):
            goal, start = state.goal, state.origin.position
            target = state.settings["oracle_goal"]  # face the object, as visual tasks require
            yaw = math.atan2(target[1] - start.y, target[0] - start.x)
            state.goal = dataclasses.replace(goal, yaw=yaw)


def no_monitor(state, reason, now):
    """Monitor-free completion: arrival or fresh near grounding ends the step directly."""
    from .connections import look_again

    state.pause(reason, now)
    settled = state.last_obs.velocity.norm() <= state.settings["stopped_mps"]
    if state.settings.get("goal_mode") != "visual":
        arrived = state.goal is not None and state.goal.arrived(state.last_obs, state.settings)
        if arrived and settled and look_again(state, now):
            return
        if arrived and settled and held_long_enough(state, now):
            state.finish_step(now)
        return
    state.visual_stop_pending = reason.startswith("fresh object proximity")
    state.replan(reason, now)


def held_long_enough(state, now):
    """A stated hold ("hold for N seconds") on a numeric arrival, without a monitor."""
    hold_ns = int(float((state.plan or {}).get("hold_s") or 0.0) * 1e9)
    if hold_ns == 0:
        return True
    if state.held_since is None:
        state.held_since = now
        state.log("hold_started", now, hold_s=hold_ns / 1e9)
    return now - state.held_since >= hold_ns


def recovery_due(state, now):
    interval = switch(state.settings, "recovery_interval_s") * 1e9
    due = (switch(state.settings, "recovery") == "periodic" and bool(state.steps)
           and now - state.last_recovery >= interval)
    if due and switch(state.settings, "review") == "idle":
        # H8 (D-187): a timed review never interrupts a step that is still making progress;
        # it waits until progress has stopped for half an interval (C10's override, D-181).
        return now - state.progress_at >= interval / 2
    return due


def bounded(position, settings):
    """The verifier's envelope check (altitude band and geofence)."""
    if not settings["min_altitude_m"] <= position.z <= settings["max_altitude_m"]:
        raise ValueError("goal outside altitude envelope")
    if math.hypot(position.x, position.y) > settings["geofence_radius_m"]:
        raise ValueError("goal outside geofence")


def unverified_direction(state, payload):
    """Without a verifier the direction is used as given; the scheduler still owns step order.

    H12 (D-187, output=lenient): a world answer written as a bare [x, y, z] list is wrapped as
    world_enu, the format repair that otherwise only happens inside the verifier (C2 failed
    every known_goal flight on "unknown goal kind" with the correct coordinates)."""
    data = json.loads(payload) if isinstance(payload, str) else dict(payload)
    target = data.get("target")
    if (switch(state.settings, "output") == "lenient" and data.get("kind") == "world"
            and isinstance(target, list) and len(target) == WORLD_CHANNELS):
        data = dict(data, target=dict(world_enu=target))
    last = not state.steps or state.step_index == len(state.steps) - 1
    return dict(data, terminal=data.get("terminal", last) and last)


def native_context(state, obs):
    """The VLA line request: the mission and the start-frame state, exactly the pilot's state."""
    from uavlab.plugins.reasoning.shared_qwen_pilot import remaining_fru

    start = remaining_fru(obs.position, state.origin.position, state.origin.yaw_rad, obs.yaw_rad)
    return dict(instruction=state.plan["objective"],
                state=[*start[:3], -math.degrees(state.yaw_total)])


def accept_native_line(state, payload, source, now):
    """Goal memory: the VLA's own Left line (body frame of the source pose) becomes the goal."""
    from .connections import measured_line
    from .goals import Goal, relative_goal

    data = json.loads(payload) if isinstance(payload, str) else payload
    measured = measured_line(state, data, source)  # H9 needs only the VLA's own box
    left = data.get("left")
    if left is None and measured is None:
        raise ValueError("VLA wrote no parseable progress line")
    if measured is None:
        limits = dict(state.settings, max_goal_m=state.settings["geofence_radius_m"])
        position, yaw = relative_goal(left, source, limits)
        terminal = True
    else:
        position, yaw, terminal = measured
    if switch(state.settings, "verifier"):
        bounded(position, state.settings)
    state.version += 1
    state.goal = Goal(state.version, position, yaw, terminal,
                      now + int(state.settings["goal_ttl_s"] * 1e9), source.seq)
    state.progress_at = state.last_monitor = now
    state.best_distance = state.best_heading = math.inf
    state.log("goal_authorized", now, position=position.model_dump(), yaw=yaw, vla_line=data,
              measured=measured is not None, terminal=terminal)
