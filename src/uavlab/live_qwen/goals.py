"""Persistent, model-authored goals and observed-state arrival checks."""

from __future__ import annotations

import math
from dataclasses import dataclass

from uavlab.contracts import Vec3
from uavlab.plugins.reasoning.shared_qwen_pilot import (
    parse_direction,
    remaining_fru,
    strict_object,
)
from uavlab.plugins.reasoning.spf import SPFPoint, point_to_enu

from .world_contract import world_target

CHANNELS = 4


@dataclass(frozen=True)
class Goal:
    version: int
    position: Vec3
    yaw: float
    terminal: bool
    expires_ns: int
    source_seq: int

    def error(self, obs):
        return remaining_fru(self.position, obs.position, obs.yaw_rad, self.yaw)

    def arrived(self, obs, limits):
        return (obs.position.distance_to(self.position) <= limits["position_m"]
                and abs(self.error(obs)[-1]) <= limits["heading_deg"])


def angle_error(a, b):
    return math.atan2(math.sin(a - b), math.cos(a - b))


def relative_goal(delta, origin, limits):
    if not isinstance(delta, list) or len(delta) != CHANNELS:
        raise ValueError("relative goal needs four channels")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in delta):
        raise ValueError("invalid relative goal")
    if math.sqrt(sum(v * v for v in delta[:3])) > limits["max_goal_m"]:
        raise ValueError("goal exceeds local distance bound")
    if abs(delta[-1]) > limits["max_goal_yaw_deg"]:
        raise ValueError("goal exceeds yaw bound")
    forward, right, up, clockwise = delta
    yaw = origin.yaw_rad
    position = Vec3(x=origin.position.x + math.cos(yaw)*forward + math.sin(yaw)*right,
                    y=origin.position.y + math.sin(yaw)*forward - math.cos(yaw)*right,
                    z=origin.position.z + up)
    return position, yaw - math.radians(clockwise)


def visual_goal(data, obs, settings):
    # travel_m here is set from measured depth, bounded by the local goal limit.
    d = parse_direction(data, settings["max_goal_m"])
    intr = obs.intrinsics
    if intr is None:
        raise ValueError("visual direction needs calibrated camera")
    position = point_to_enu(
        SPFPoint(d["u"], d["v"], 1), position=obs.position, yaw_rad=obs.yaw_rad,
        width=intr.width, height=intr.height, fx=intr.fx, fy=intr.fy,
        cx=intr.cx, cy=intr.cy, camera_pitch_rad=settings["camera_pitch_rad"],
        distance_m=d["travel_m"], min_altitude_m=settings["min_altitude_m"],
    )
    if settings.get("visual_altitude", "ray") == "hold":
        # The box centre of a tall object sits above its body, so following the
        # ray climbs (D-152: +1.1 m on approach_hover). Keep bearing, hold height.
        position = Vec3(x=position.x, y=position.y, z=obs.position.z)
    yaw = math.atan2(position.y-obs.position.y, position.x-obs.position.x)
    return position, yaw


def interpret_goal(payload, source, origin, settings):
    value = strict_object(payload, ("kind", "target", "terminal"))
    if type(value["terminal"]) is not bool:
        raise ValueError("terminal must be boolean")
    if value["kind"] == "relative":
        position, yaw = relative_goal(value["target"], origin, settings)
    elif value["kind"] == "world" and world_target(value["target"]):
        position = Vec3(**dict(zip(("x", "y", "z"), value["target"]["world_enu"], strict=True)))
        yaw = origin.yaw_rad
    elif value["kind"] == "visual":
        position, yaw = visual_goal(value["target"], source, settings)
    else:
        raise ValueError("unknown goal kind")
    if not settings["min_altitude_m"] <= position.z <= settings["max_altitude_m"]:
        raise ValueError("goal outside altitude envelope")
    if math.hypot(position.x, position.y) > settings["geofence_radius_m"]:
        raise ValueError("goal outside geofence")
    return position, yaw, value["terminal"]
