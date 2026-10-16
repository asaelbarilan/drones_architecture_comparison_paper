"""Strict visible-object localization, separate from bounded waypoint geometry."""

import json
import math

import numpy as np

from uavlab.core.frame_store import global_store

GROUNDING = '''Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: '''
BOX_CHANNELS = 4
COORD_MAX = 1000
NEAR_OBJECT_M = 1.5

VISUAL_PLANNER = '''Plan the original visual mission in order. Return ONLY JSON with
one key steps, a list of objects each having objective and target strings.
Each target is the object's identifying NOUN PHRASE, not an action instruction.
Each objective preserves the requested action, object identity and stop condition.
Approach an object and stop nearby is ONE step, not approach followed by stop.
Use multiple steps only for distinct explicitly requested destinations/actions.
Do not invent coordinates or numeric moves. Preserve the entire original goal.
Context: '''


def grounded_direction(payload):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if set(data) != {"target_visible", "box"} or type(data["target_visible"]) is not bool:
        raise ValueError("grounding requires visibility and box")
    box = data["box"]
    if not data["target_visible"]:
        if box is not None:
            raise ValueError("absent object cannot have a box")
        return None
    if not isinstance(box, list) or len(box) != BOX_CHANNELS:
        raise ValueError("visible object requires box")
    if any(type(v) is not int or not 0 <= v <= COORD_MAX for v in box):
        raise ValueError("invalid normalized box")
    left, top, right, bottom = box
    if left >= right or top >= bottom:
        raise ValueError("empty or reversed box")
    return dict(kind="visual", target=dict(
        u=(left+right)//2, v=(top+bottom)//2, travel_m=1.0,
        target_visible=True, box=box))


def capture_depth(obs):
    stored = global_store().get(obs.depth.uri) if obs.depth else None
    return None if stored is None else np.array(stored, copy=True)


def observed_range(proposal, obs, stored=None):
    """Range along the fresh model-selected pixel; no simulator object metadata."""
    if obs.depth is None or obs.intrinsics is None:
        return None
    if stored is None:
        stored = global_store().get(obs.depth.uri)
    if stored is None:
        return None
    depth, intr = np.asarray(stored), obs.intrinsics
    if depth.shape != (intr.height, intr.width):
        return None
    target = proposal["target"]
    x = min(intr.width-1, int(target["u"]*intr.width/COORD_MAX))
    y = min(intr.height-1, int(target["v"]*intr.height/COORD_MAX))
    forward = float(depth[y, x])
    if not math.isfinite(forward) or forward <= 0:
        return None
    return forward * math.sqrt(1+((x-intr.cx)/intr.fx)**2+((y-intr.cy)/intr.fy)**2)
