"""Ordered model-authored mission contracts; evaluator targets never enter here."""

import json
import math

MAX_STEPS = 8
MAX_TEXT = 400
POSE_CHANNELS = 4


def parse_steps(payload):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if set(data) != {"steps"} or not isinstance(data["steps"], list):
        raise ValueError("planner requires ordered steps")
    if not 1 <= len(data["steps"]) <= MAX_STEPS:
        raise ValueError("planner requires 1..8 steps")
    for step in data["steps"]:
        if set(step) != {"objective", "target"}:
            raise ValueError("step requires objective and target")
        if not isinstance(step["objective"], str) or not 1 <= len(step["objective"]) <= MAX_TEXT:
            raise ValueError("invalid step objective")
        validate_target(step["target"])
    return accumulate_steps(json.loads(json.dumps(data["steps"])))


def accumulate_steps(steps):
    pose = [0, 0, 0, 0]
    for step in steps:
        if isinstance(step["target"], list):
            if pose is None:
                raise ValueError("numeric step after visual motion needs explicit localization")
            pose = [a+b for a, b in zip(pose, step["target"], strict=True)]
            step["target"] = pose
        else:
            pose = None
    return steps


def validate_target(target):
    if isinstance(target, str) and 1 <= len(target) <= MAX_TEXT:
        return  # A visual description, not a numeric pose claim.
    if not isinstance(target, list) or len(target) != POSE_CHANNELS:
        raise ValueError("target must be numeric pose or visual description")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in target):
        raise ValueError("nonfinite/non-numeric mission target")


def accept_plan(state, payload, now):
    steps = parse_steps(payload)
    if state.settings.get("goal_mode") == "visual" and any(
            not isinstance(step["target"], str) for step in steps):
        raise ValueError("visual mission requires visual descriptions, not invented numeric goals")
    if state.steps and steps != state.steps:
        raise ValueError("replanning cannot replace committed mission steps")
    state.steps = steps
    state.plan = dict(steps[state.step_index])
    state.log("mission_plan_committed", now, mission=state.mission.instruction,
              authored=payload, steps=steps, step_index=state.step_index)


def validate_direction(state, payload):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not state.steps:
        return data  # Manually constructed scheduler fixtures have no committed plan.
    expected_terminal = state.step_index == len(state.steps)-1
    target = state.steps[state.step_index]["target"]
    if isinstance(target, list):
        if data["kind"] != "relative" or data["target"] != target:
            raise ValueError("direction changed committed numeric step")
        if data.get("terminal", expected_terminal) != expected_terminal:
            raise ValueError("direction cannot skip remaining mission steps")
    else:
        if data["kind"] != "visual":
            raise ValueError("visual objective requires camera grounding")
        if data.get("terminal", False) and not expected_terminal:
            raise ValueError("visual direction cannot skip remaining mission steps")
    return dict(data, terminal=data.get("terminal", expected_terminal))
