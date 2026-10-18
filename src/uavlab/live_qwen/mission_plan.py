"""Ordered model-authored mission contracts; evaluator targets never enter here."""

import json
import math
import re

from .world_contract import normalize_world, world_target

MAX_STEPS = 8
MAX_TEXT = 400
POSE_CHANNELS = 4
# Planner-extracted stop parameters (D-158): stated hover distance and hold time.
OPTIONAL = {"standoff_m": (0.5, 3.0), "hold_s": (0.0, 30.0)}
# The 4B planner omits these fields (D-158 first run), so explicit numbers in the
# step's own public text are read directly, as world_contract does for coordinates.
STATED = {
    "standoff_m": re.compile(r"\babout\s+(\d+(?:\.\d+)?)\s*(?:m|metres?|meters?)\s+"
                             r"(?:before|from|in front of|away from)\b", re.IGNORECASE),
    "hold_s": re.compile(r"\bhold\w*\s+(?:position\s+)?for\s+(\d+(?:\.\d+)?)\s+"
                         r"(?:continuous\s+)?seconds?\b", re.IGNORECASE),
}


def parse_steps(payload):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if set(data) != {"steps"} or not isinstance(data["steps"], list):
        raise ValueError("planner requires ordered steps")
    if not 1 <= len(data["steps"]) <= MAX_STEPS:
        raise ValueError("planner requires 1..8 steps")
    for step in data["steps"]:
        if not {"objective", "target"} <= set(step) <= {"objective", "target", *OPTIONAL}:
            raise ValueError("step requires objective and target")
        for key, (low, high) in OPTIONAL.items():
            value = step.get(key)
            if value is not None and (type(value) not in (int, float) or not low <= value <= high):
                raise ValueError(f"invalid step {key}")
        if not isinstance(step["objective"], str) or not 1 <= len(step["objective"]) <= MAX_TEXT:
            raise ValueError("invalid step objective")
        validate_target(step["target"])
    steps = json.loads(json.dumps(data["steps"]))
    for step in steps:
        add_stated_fields(step)
    return accumulate_steps(steps)


def add_stated_fields(step):
    for key, pattern in STATED.items():
        match = pattern.search(step["objective"])
        low, high = OPTIONAL[key]
        if step.get(key) is None and match and low <= float(match.group(1)) <= high:
            step[key] = float(match.group(1))


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
    if world_target(target):
        return
    if isinstance(target, str) and 1 <= len(target) <= MAX_TEXT:
        return  # A visual description, not a numeric pose claim.
    if not isinstance(target, list) or len(target) != POSE_CHANNELS:
        raise ValueError("target must be numeric pose or visual description")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in target):
        raise ValueError("nonfinite/non-numeric mission target")


def accept_plan(state, payload, now):
    steps = parse_steps(normalize_world(payload, state.mission.instruction))
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
    if isinstance(target, list) or world_target(target):
        expected_kind = "world" if world_target(target) else "relative"
        if (world_target(target) and data["kind"] == "world"
                and data["target"] == target["world_enu"]):
            data = dict(data, target=target)
        if data["kind"] != expected_kind or data["target"] != target:
            raise ValueError("direction changed committed numeric step")
        if data.get("terminal", expected_terminal) != expected_terminal:
            raise ValueError("direction cannot skip remaining mission steps")
    else:
        if data["kind"] != "visual":
            raise ValueError("visual objective requires camera grounding")
        if data.get("terminal", False) and not expected_terminal:
            raise ValueError("visual direction cannot skip remaining mission steps")
    return dict(data, terminal=data.get("terminal", expected_terminal))
