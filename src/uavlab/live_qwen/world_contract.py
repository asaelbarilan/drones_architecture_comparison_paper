"""Explicit world coordinates come from mission text, never evaluator metadata."""

import json
import math
import re

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
POSITION_CHANNELS = 3
WORLD = re.compile(r"world\s+ENU\s+coordinate\s*\(\s*(" + NUMBER +
                   r")\s*,\s*(" + NUMBER + r")\s*,\s*(" + NUMBER + r")\s*\)", re.I)


def explicit_world(instruction):
    matches = WORLD.findall(instruction)
    return [float(v) for v in matches[0]] if len(matches) == 1 else None


def world_target(target):
    if not isinstance(target, dict) or set(target) != {"world_enu"}:
        return False
    values = target["world_enu"]
    return (isinstance(values, list) and len(values) == POSITION_CHANNELS
            and all(type(v) in (int, float) and math.isfinite(v) for v in values))


def normalize_world(payload, instruction):
    """Accept a three-coordinate answer only when it exactly repeats public ENU text."""
    data = json.loads(payload) if isinstance(payload, str) else json.loads(json.dumps(payload))
    public = explicit_world(instruction)
    for step in data.get("steps", []):
        target = step.get("target")
        if public is not None and target == public:
            step["target"] = {"world_enu": public}
        elif isinstance(target, dict) and (not world_target(target)
                                          or public != target["world_enu"]):
            raise ValueError("world target must exactly match explicit mission coordinates")
    return data
