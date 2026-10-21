"""C1 (D-161): an AerialClaw-style LLM skill agent on the shared live runtime.

The text-only model chooses ONE skill per turn from the mission, its measured pose and the
results of its previous skills. The runtime executes the skill with the same machinery as every
other architecture (classical pilot, visual grounding legs, shield) and reports the outcome back.
Perception is a tool (detect / approach use the shared grounding role); the agent never sees
the camera image itself and never sees evaluator truth.
"""

import json
import math

from uavlab.contracts import Vec3, s_to_ns

from .architecture import bounded, switch
from .goals import Goal, relative_goal
from .grounding import grounded_direction
from .visual_progress import record_grounding

SKILLS = ("goto", "approach", "detect", "scan", "hover", "done")
MAX_TURNS = 24
HISTORY = 12
MAX_HOVER_S = 30
SCAN_DEG = 45
MAX_TEXT = 200
ENU_CHANNELS = 3

SKILL = '''You are the mission agent of a quadrotor. Choose exactly ONE skill per turn.
Return JSON only: {"skill":"...","args":{...},"reason":"at most 15 words"}.
Skills:
goto: args {"forward_m":F,"right_m":R,"up_m":U,"clockwise_deg":C} relative to the CURRENT
 pose and heading (at most 10 m), or {"world_enu":[x,y,z]} for an explicit world coordinate.
approach: args {"object":"description"}: fly to that visible object, stop about 1 m before it.
detect: args {"object":"description"}: look with the camera; reports visible, image_x, range.
scan: args {}: turn 45 degrees clockwise in place to look elsewhere.
hover: args {"seconds":N}: stay still N seconds (at most 30).
done: args {}: ONLY when the WHOLE mission is complete.
Use the history: do not repeat a skill that just failed in the same way. Context: '''


def active(state):
    return switch(state.settings, "goal_source") == "skills"


def enu(position):
    return [round(position.x, 2), round(position.y, 2), round(position.z, 2)]


def skill_context(state, obs):
    return dict(mission=state.mission.instruction, turn=state.skill_turns, max_turns=MAX_TURNS,
                position_enu=enu(obs.position), start_enu=enu(state.origin.position),
                heading_deg_from_start=round(-math.degrees(state.yaw_total), 1),
                history=state.skill_history)


def parse_skill(payload):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict) or set(data) != {"skill", "args", "reason"}:
        raise ValueError("skill turn requires skill, args and reason")
    if data["skill"] not in SKILLS or not isinstance(data["args"], dict):
        raise ValueError("unknown skill or invalid args")
    if not isinstance(data["reason"], str) or len(data["reason"]) > MAX_TEXT:
        raise ValueError("invalid skill reason")
    if data["skill"] in ("approach", "detect"):
        target = data["args"].get("object")
        if not isinstance(target, str) or not 1 <= len(target) <= MAX_TEXT:
            raise ValueError("approach/detect need an object description")
    return data


def accept_skill(state, payload, now):
    data = parse_skill(payload)
    state.skill, state.skill_turns = data, state.skill_turns + 1
    state.log("skill_selected", now, skill=data, turn=state.skill_turns)
    kind, args, obs = data["skill"], data["args"], state.last_obs
    if kind == "done":
        state.stopped = True
        state.pause("skill agent declared the mission done", now)
    elif kind == "hover":
        seconds = args.get("seconds", 0)
        if type(seconds) not in (int, float) or not 0 <= seconds <= MAX_HOVER_S:
            raise ValueError("hover seconds must be 0..30")
        state.pause("hover skill", now)
        state.skill_until = now + s_to_ns(seconds)
    elif kind in ("approach", "detect"):
        state.settings["goal_mode"] = "visual"
        state.steps = [dict(objective=f"{kind} {args['object']}", target=args["object"])]
        state.plan = dict(state.steps[0])
    else:
        numeric_skill(state, kind, args, obs, now)


def numeric_skill(state, kind, args, obs, now):
    """goto / scan become one persistent numeric goal for the classical pilot."""
    state.settings["goal_mode"] = "numeric"
    if kind == "scan":
        position, yaw = obs.position, obs.yaw_rad - math.radians(SCAN_DEG)
    elif "world_enu" in args:
        position, yaw = world_point(args["world_enu"]), obs.yaw_rad
    else:
        keys = ("forward_m", "right_m", "up_m", "clockwise_deg")
        delta = [args.get(key, 0) for key in keys]
        position, yaw = relative_goal(delta, obs, state.settings)
    if switch(state.settings, "verifier"):
        bounded(position, state.settings)
    state.steps = [dict(objective=kind, target=[position.x, position.y, position.z, yaw])]
    state.plan = dict(state.steps[0])
    state.version += 1
    state.goal = Goal(state.version, position, yaw, False,
                      now + s_to_ns(state.settings["goal_ttl_s"]), obs.seq)
    state.progress_at = state.last_monitor = now
    state.best_distance = state.best_heading = math.inf
    state.log("goal_authorized", now, position=position.model_dump(), yaw=yaw, skill=kind)


def world_point(values):
    if (not isinstance(values, list) or len(values) != ENU_CHANNELS
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in values)):
        raise ValueError("world_enu needs three finite coordinates")
    return Vec3(x=values[0], y=values[1], z=values[2])


def detected(state, payload, source, now):
    """detect skill: one grounding call, reported back without moving."""
    proposal = grounded_direction(payload)
    if proposal is None:
        return finished(state, "not visible", now)
    record_grounding(state, proposal, source, now, now)
    target = proposal["target"]
    result = dict(visible=True, image_x=target.get("u"), range_m=state.visual_evidence["range_m"])
    return finished(state, json.dumps(result), now)


def finished(state, result, now):
    """The current skill ended (completed or not); hand control back to the agent."""
    skill = state.skill or {}
    entry = dict(skill=skill.get("skill"), args=skill.get("args"), result=result)
    state.skill_history = [*state.skill_history, entry][-HISTORY:]
    state.log("skill_finished", now, **entry)
    state.steps, state.step_index, state.skill = [], 0, None
    state.visual_stop_pending, state.target_missing = False, False
    state.replan("skill finished: " + result, now)
    if state.skill_turns >= MAX_TURNS:
        state.failed = True
        state.log("failure", now, error="skill turn limit reached")


def skill_tick(state, now):
    """Hover waits; returns True while the hover skill still owns the tick."""
    if state.skill is None or state.skill["skill"] != "hover":
        return False
    if now >= state.skill_until:
        finished(state, "hovered", now)
        return False  # the agent's next turn can be submitted on this same tick
    return True
