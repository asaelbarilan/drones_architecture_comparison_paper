"""D-132 explicit four-role shared-base architecture, development only.

The semantic planner authors the objective. Direction selects a camera point.
The monitor may hold/replan/stop. Only the trained pilot produces motion deltas.
No simulator labels, target coordinates or oracle path enter the model prompts.
"""

from __future__ import annotations

import base64
import io
import json
import math

from uavlab.contracts import DecisionKind, KinematicAction, MissionDirective, ProgressLabel, Vec3
from uavlab.core.frame_store import global_store
from uavlab.core.registry import register
from uavlab.interfaces import InferenceRequest
from uavlab.plugins.reasoning.base import BasePolicy
from uavlab.plugins.reasoning.spf import SPFPoint, point_to_enu

PLANNER = (
    "You are the mission planner. Return only JSON with exactly "
    '"objective" (one short actionable instruction) and "target" (visual description). '
    "Use the mission and feedback; never invent coordinates or claim completion. Mission: "
)
DIRECTION = (
    "You select the next local flight direction from the current camera. "
    'Return only JSON with exactly "u", "v" (integer image coordinates 0..1000), '
    '"travel_m" (0.25..3 metres of intended forward travel), '
    '"target_visible" (boolean), "box" (target bbox [x1,y1,x2,y2] in 0..1000, '
    "or null when absent). Point toward the requested target if visible, otherwise "
    "choose visible free space. Do not invent a target box. Objective: "
)
MONITOR = (
    "You monitor progress using the current image, objective and measured local-goal error. "
    'Return only JSON with exactly "status" (continue, hold, replan, or stop) and '
    '"reason" (short text). Stop only if the mission is visibly accomplished; reaching '
    "one intermediate point is not mission completion. If blocked/uncertain hold or replan. "
)


def strict_object(payload, keys):
    value = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f"Expected exactly {keys}")
    return value


def parse_plan(payload):
    p = strict_object(payload, ("objective", "target"))
    if any(not isinstance(v, str) or not v.strip() or len(v) > 400 for v in p.values()):
        raise ValueError("Invalid planner strings")
    return p


def parse_direction(payload):
    p = strict_object(payload, ("u", "v", "travel_m", "target_visible", "box"))
    if any(type(p[k]) is not int or not 0 <= p[k] <= 1000 for k in ("u", "v")):
        raise ValueError("Invalid camera point")
    if type(p["travel_m"]) not in (int, float) or not 0.25 <= p["travel_m"] <= 3:
        raise ValueError("Invalid travel distance")
    if type(p["target_visible"]) is not bool:
        raise ValueError("Invalid visibility")
    b = p["box"]
    if p["target_visible"]:
        if (
            not isinstance(b, list)
            or len(b) != 4
            or any(type(v) not in (int, float) or not 0 <= v <= 1000 for v in b)
            or not (b[0] < b[2] and b[1] < b[3])
        ):
            raise ValueError("Visible target requires ordered normalized box")
    elif b is not None:
        raise ValueError("Absent target cannot have a box")
    return p


def parse_monitor(payload):
    p = strict_object(payload, ("status", "reason"))
    if p["status"] not in {"continue", "hold", "replan", "stop"}:
        raise ValueError("Unknown monitor status")
    if not isinstance(p["reason"], str) or len(p["reason"]) > 500:
        raise ValueError("Invalid monitor reason")
    return p


def remaining_fru(goal, position, yaw, goal_yaw):
    """ENU (CCW yaw) -> trained forward/right/up, clockwise degrees."""
    dx, dy = goal.x - position.x, goal.y - position.y
    return [
        math.cos(yaw) * dx + math.sin(yaw) * dy,
        math.sin(yaw) * dx - math.cos(yaw) * dy,
        goal.z - position.z,
        -math.degrees(math.atan2(math.sin(goal_yaw - yaw), math.cos(goal_yaw - yaw))),
    ]


def pilot_action(step, yaw, duration=0.5, max_speed=2.0, max_yaw_rate=1.0):
    if len(step) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in step):
        raise ValueError("Invalid pilot step")
    if duration <= 0 or max_speed <= 0 or max_yaw_rate <= 0:
        raise ValueError("Invalid control limits")
    forward, right, up, clockwise = step
    east = math.cos(yaw) * forward + math.sin(yaw) * right
    north = math.sin(yaw) * forward - math.cos(yaw) * right
    # Preserve displacement by extending execution duration, never clip silently.
    dt = max(
        duration, math.sqrt(east**2 + north**2 + up**2) / max_speed, abs(clockwise) / max_yaw_rate
    )
    return KinematicAction(
        velocity=Vec3(x=east / dt, y=north / dt, z=up / dt),
        yaw_rate_rps=-clockwise / dt,
        duration_s=dt,
    )


@register("policy", "shared_qwen_pilot")
class SharedQwenPilot(BasePolicy):
    requires_vision = True
    requires_real_inference = True

    def __init__(self, **params):
        params.setdefault("model_id", "qwen3-vl-4b-d207-shared")
        super().__init__(**params)
        self.camera_pitch = float(params.get("camera_pitch_rad", -0.10))
        self._plan = self._goal = self._direction = None
        self._goal_yaw = 0.0
        self._action_until = 0
        self._feedback = "initial observation"
        self._origin = None
        self._origin_yaw = self._last_yaw = self._yaw_total = 0.0

    @property
    def name(self):
        return "shared_qwen_pilot"

    @property
    def emits(self):
        return ("kinematic_action", "mission_directive")

    def reset(self, mission, seed):
        super().reset(mission, seed)
        self._plan = self._goal = self._direction = None
        self._action_until = 0
        self._feedback = "initial observation"
        self._origin = None
        self._origin_yaw = self._last_yaw = self._yaw_total = 0.0

    async def _call(self, ctx, role, prompt, image=None):
        request = InferenceRequest(
            model_id=self.model_id,
            role=role,
            prompt_hash=f"d132:{role}:v1",
            prompt=prompt,
            images=(image,) if image else (),
            image_count=int(image is not None),
            observation_seq=ctx.observation.seq,
        )
        return (await self.services.inference.invoke(request)).payload

    def _hold(self, ctx, reason):
        return self.envelope(
            ctx,
            DecisionKind.KINEMATIC_ACTION,
            KinematicAction(velocity=Vec3(x=0, y=0, z=0), duration_s=0.5),
            0.0,
            note=reason,
        )

    async def decide(self, ctx):
        if ctx.t_sim_ns < self._action_until:
            return None
        if self.services is None or self.services.inference is None:
            raise RuntimeError("shared Qwen inference required")
        obs = ctx.observation
        if self._origin is None:
            self._origin, self._origin_yaw, self._last_yaw = obs.position, obs.yaw_rad, obs.yaw_rad
        self._yaw_total += math.atan2(
            math.sin(obs.yaw_rad - self._last_yaw), math.cos(obs.yaw_rad - self._last_yaw)
        )
        self._last_yaw = obs.yaw_rad
        if obs.rgb is None or obs.intrinsics is None:
            raise ValueError("Current RGB and calibrated intrinsics required")
        image = global_store().get(obs.rgb.uri)
        if image is None:
            raise ValueError("Unresolved current RGB")
        b = io.BytesIO()
        image.convert("RGB").save(b, format="PNG")
        encoded = base64.b64encode(b.getvalue()).decode("ascii")
        if ctx.last_routing_feedback and not ctx.last_routing_feedback.accepted:
            self._feedback = ctx.last_routing_feedback.reason
            self._plan = self._goal = None
        try:
            if self._plan is None:
                self._plan = parse_plan(
                    await self._call(
                        ctx,
                        "planner",
                        PLANNER + ctx.mission.instruction + " Feedback: " + self._feedback,
                    )
                )
            # Refresh image-space boxes every observation, but retain the anchored
            # goal until the monitor has judged arrival at that existing goal.
            self._direction = parse_direction(
                await self._call(ctx, "direction", DIRECTION + json.dumps(self._plan), encoded)
            )
            if self._goal is None:
                d, intr = self._direction, obs.intrinsics
                self._goal = point_to_enu(
                    SPFPoint(d["u"], d["v"], 1),
                    position=obs.position,
                    yaw_rad=obs.yaw_rad,
                    width=intr.width,
                    height=intr.height,
                    fx=intr.fx,
                    fy=intr.fy,
                    cx=intr.cx,
                    cy=intr.cy,
                    camera_pitch_rad=self.camera_pitch,
                    distance_m=d["travel_m"],
                    min_altitude_m=ctx.mission.constraints.min_altitude_m,
                )
                self._goal_yaw = math.atan2(
                    self._goal.y - obs.position.y, self._goal.x - obs.position.x
                )
            remaining = remaining_fru(self._goal, obs.position, obs.yaw_rad, self._goal_yaw)
            monitor = parse_monitor(
                await self._call(
                    ctx,
                    "monitor",
                    MONITOR
                    + json.dumps(
                        {
                            "mission": ctx.mission.instruction,
                            "plan": self._plan,
                            "local_goal_remaining_fru_m_clockwise_deg": remaining,
                            "speed_mps": obs.velocity.norm(),
                        }
                    ),
                    encoded,
                )
            )
            if monitor["status"] == "replan":
                self._feedback = monitor["reason"]
                self._plan = self._goal = None
                return self._hold(ctx, "monitor requests replan")
            if monitor["status"] == "hold":
                return self._hold(ctx, monitor["reason"])
            if monitor["status"] == "stop":
                # A visual STOP alone cannot terminate at speed or far from the
                # current observed goal. This is not an oracle mission-success test.
                if (
                    obs.position.distance_to(self._goal) > 0.5
                    or abs(remaining[3]) > 5
                    or obs.velocity.norm() > 0.2
                ):
                    return self._hold(ctx, "monitor stop rejected: local arrival/heading/speed")
                return self.envelope(
                    ctx,
                    DecisionKind.MISSION_DIRECTIVE,
                    MissionDirective(label=ProgressLabel.STOP, rationale=monitor["reason"]),
                    0.5,
                )
            if obs.position.distance_to(self._goal) <= 0.5:
                # Continue means this was an intermediate waypoint. Re-anchor on
                # the next observation; never move the goal before the stop check.
                self._goal = None
                return self._hold(ctx, "intermediate waypoint reached; select next goal")
            payload = await self._call(
                ctx,
                "pilot",
                json.dumps(
                    {
                        "instruction": self._plan["objective"],
                        "state": [
                            *remaining_fru(
                                obs.position, self._origin, self._origin_yaw, obs.yaw_rad
                            )[:3],
                            -math.degrees(self._yaw_total),
                        ],
                        "remaining": remaining,
                        "box": self._direction["box"],
                    }
                ),
                encoded,
            )
            steps = payload["steps_fru_m_yaw_rad"]
            if len(steps) != 8:
                raise ValueError("Pilot must return trained eight-action chunk")
            action = pilot_action(
                steps[0], obs.yaw_rad, max_speed=ctx.mission.constraints.max_speed_mps
            )
            self._action_until = self.services.clock.now_ns() + int(action.duration_s * 1e9)
            return self.envelope(
                ctx,
                DecisionKind.KINEMATIC_ACTION,
                action,
                0.5,
                note="VLA first step; seven suffix steps discarded for feedback",
                extra={
                    "remaining": json.dumps(remaining),
                    "local_goal": self._goal.model_dump_json(),
                },
            )
        except (ValueError, KeyError, TypeError) as exc:
            self._feedback = f"Role contract rejected: {exc}"
            return self._hold(ctx, self._feedback)
