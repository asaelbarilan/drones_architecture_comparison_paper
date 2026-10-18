"""When a visual step is done: stated standoff, stated hold time, object below the camera.

All inputs are model-authored plan fields or onboard measurements; evaluator
geometry never enters here (D-158).
"""

import math

from uavlab.contracts import s_to_ns
from uavlab.plugins.reasoning.spf import SPFPoint, point_to_enu

from .grounding import COORD_MAX, NEAR_OBJECT_M

NEAR_MARGIN_M = 0.25


def stated_standoff(state):
    """Planner-extracted hover distance, used only when tighter than the default."""
    value = (state.plan or {}).get("standoff_m")
    return value if value is not None and value < NEAR_OBJECT_M else None


def near_limit(state):
    standoff = stated_standoff(state)
    return NEAR_OBJECT_M if standoff is None else standoff + NEAR_MARGIN_M


def aim_standoff(state):
    standoff = stated_standoff(state)
    return NEAR_OBJECT_M - NEAR_MARGIN_M if standoff is None else standoff


def object_position(proposal, source, range_m, settings):
    """World estimate of the grounded object from its pixel ray and measured range."""
    intr = source.intrinsics
    if range_m is None or intr is None:
        return None
    target = proposal["target"]
    x = target["u"] * intr.width / COORD_MAX
    y = target["v"] * intr.height / COORD_MAX
    forward = range_m / math.sqrt(1 + ((x - intr.cx) / intr.fx) ** 2
                                  + ((y - intr.cy) / intr.fy) ** 2)
    return point_to_enu(
        SPFPoint(target["u"], target["v"], 1), position=source.position, yaw_rad=source.yaw_rad,
        width=intr.width, height=intr.height, fx=intr.fx, fy=intr.fy, cx=intr.cx, cy=intr.cy,
        camera_pitch_rad=settings["camera_pitch_rad"], distance_m=forward, min_altitude_m=-1e9)


def remember_object(state, proposal, source, range_m, now):
    position = object_position(proposal, source, range_m, state.settings)
    if position is not None:
        state.object_memory = dict(position=position, target=state.plan["target"], seen_ns=now)


def object_below(state, obs, now):
    """Object vanished from view while the drone is over its last estimated position.

    A forward camera cannot see an object under the drone; a recent estimate of
    the same target within the near limit horizontally means arrival, not loss.
    """
    memory = state.object_memory
    if memory is None or memory["target"] != state.plan["target"]:
        return False
    if now - memory["seen_ns"] > s_to_ns(state.settings["cognition_ttl_s"]):
        return False
    p = memory["position"]
    horizontal = math.hypot(p.x - obs.position.x, p.y - obs.position.y)
    return horizontal <= near_limit(state) and obs.velocity.norm() <= state.settings["stopped_mps"]


def hold_required_ns(state):
    return s_to_ns(float((state.plan or {}).get("hold_s") or 0.0))


def start_hold(state, now):
    state.hold_started = now
    state.hold_until = now + hold_required_ns(state)
    state.pause("holding position for the requested time", now)
    state.log("hold_started", now, hold_s=hold_required_ns(state) / 1e9)
