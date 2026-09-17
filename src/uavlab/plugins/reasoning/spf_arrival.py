"""D-129 development extension: native SPF motion plus RGB-D arrival evidence.

This is not native SPF. Two distinct VLM localizations establish a short-lived
surface-point track. Near that point we hold a measured vehicle pose and emit
STOP only from a fresh, low-speed observation. Goal-center truth is never read.
"""

from __future__ import annotations

import json
import math
from typing import Any

import numpy as np

from uavlab.contracts import DecisionKind, MissionDirective, ProgressLabel, Vec3, WaypointGoal
from uavlab.core.frame_store import global_store
from uavlab.core.registry import register
from uavlab.interfaces import InferenceRequest
from uavlab.plugins.reasoning.spf import SPFWaypointPolicy

LOCALIZE_PROMPT = (
    "Locate the {target} in this image. This is a localization test, not navigation. "
    "Return visible=true and a tight bounding box around ONLY the visible {target}, "
    "excluding adjacent gray buildings. Box order is [left,top,right,bottom], using a "
    "0..999 grid: (0,0) is the image top-left and (999,999) bottom-right. "
    "If no {target} is visible, return visible=false and box=[0,0,0,0]. "
    "Gray or green structures are not the {target}. Evidence should briefly describe "
    "what is actually visible. Return JSON with evidence, visible and box."
)
LOCALIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "evidence": {"type": "string", "maxLength": 120},
        "visible": {"type": "boolean"},
        "box": {
            "type": "array",
            "items": {"type": "integer", "minimum": 0, "maximum": 999},
            "minItems": 4,
            "maxItems": 4,
        },
    },
    "required": ["evidence", "visible", "box"],
    "additionalProperties": False,
}


def parse_localization(text):
    item = json.loads(text)
    if not isinstance(item, dict) or set(item) != {"evidence", "visible", "box"}:
        raise ValueError("localization fields")
    b = item["box"]
    if (
        type(item["visible"]) is not bool
        or not isinstance(item["evidence"], str)
        or len(item["evidence"]) > 120
        or not isinstance(b, list)
        or len(b) != 4
        or any(type(x) is not int or not 0 <= x <= 999 for x in b)
    ):
        raise ValueError("localization types/ranges")
    if item["visible"] and not (b[0] < b[2] and b[1] < b[3]):
        raise ValueError("empty or inverted box")
    if not item["visible"] and b != [0, 0, 0, 0]:
        raise ValueError("absent target has nonempty box")
    return item


def localized_point(obs, depth, box, pitch_rad):
    """Use actual intrinsics and synchronized camera-forward depth at a VLM pixel."""
    intr = obs.intrinsics
    if intr is None or depth is None or depth.shape != (intr.height, intr.width):
        return None
    if not all(math.isfinite(x) and x > 0 for x in (intr.fx, intr.fy)):
        return None
    u = (box[0] + box[2]) * 0.5 * (intr.width - 1) / 999
    v = (box[1] + box[3]) * 0.5 * (intr.height - 1) / 999
    d = float(depth[round(v), round(u)])
    if not math.isfinite(d) or not 0.05 < d < 40:
        return None
    right, up = (u - intr.cx) * d / intr.fx, (intr.cy - v) * d / intr.fy
    cp, sp = math.cos(-pitch_rad), math.sin(-pitch_rad)
    forward, vertical = d * cp + up * sp, -d * sp + up * cp
    cy, sy = math.cos(obs.yaw_rad), math.sin(obs.yaw_rad)
    return Vec3(
        x=obs.position.x + forward * cy + right * sy,
        y=obs.position.y + forward * sy - right * cy,
        z=obs.position.z + vertical,
    )


@register("policy", "spf_rgbd_arrival")
class SPFRGBDArrivalPolicy(SPFWaypointPolicy):
    """Named surface-arrival extension; retains the original SPF movement prompt."""

    def __init__(self, **params: Any):
        super().__init__(**params)
        self.arrival_enabled = self.self_terminate
        self.self_terminate = False  # Native ordinal labels never terminate this extension.
        self.surface_stop_radius_m = float(params.get("surface_stop_radius_m", 1.0))
        self.arrival_ttl_s = float(params.get("arrival_ttl_s", 6.0))
        self.target_consistency_m = float(params.get("target_consistency_m", 0.75))
        self.stop_speed_mps = float(params.get("stop_speed_mps", 0.15))
        self.localization_target = str(params.get("localization_target", "red pillar"))
        if self.localization_target != "red pillar":
            raise ValueError("D-129 localization prompt is scoped to red pillar")
        if not (
            0 < self.surface_stop_radius_m <= 2
            and 0 < self.arrival_ttl_s <= 6
            and 0 < self.target_consistency_m <= 1
            and 0 < self.stop_speed_mps <= 0.2
        ):
            raise ValueError("arrival parameters outside declared development bounds")
        self._clear_arrival()
        self.localization_calls = 0
        self.localization_errors = 0
        self.arrival_holds = 0

    @property
    def name(self):
        return "spf_rgbd_arrival"

    def _clear_arrival(self):
        self._target_point = None
        self._target_t_ns = -1
        self._target_seq = -1
        self._confirmations = 0
        self._hold_position = None

    def reset(self, mission, seed):
        super().reset(mission, seed)
        if mission.task_family.value not in {"semantic_goal_nav", "long_horizon_nav"}:
            raise ValueError("D-129 supports stationary single-target navigation only")
        self._clear_arrival()
        self.localization_calls = self.localization_errors = self.arrival_holds = 0

    def _fresh(self, obs):
        age = (obs.t_sim_ns - self._target_t_ns) / 1e9
        return self._target_point is not None and 0 <= age <= self.arrival_ttl_s

    def _update_target(self, obs, point):
        if obs.seq <= self._target_seq:
            return
        consistent = (
            point is not None
            and self._fresh(obs)
            and point.distance_to(self._target_point) <= self.target_consistency_m
        )
        self._confirmations = self._confirmations + 1 if consistent else int(point is not None)
        self._target_point = point
        self._target_seq, self._target_t_ns = obs.seq, obs.t_sim_ns

    def _evidence(self, obs):
        return {
            "implementation": "spf_rgbd_arrival_extension_d129",
            "arrival_source_seq": str(self._target_seq),
            "arrival_source_t_ns": str(self._target_t_ns),
            "arrival_confirmations": str(self._confirmations),
            "arrival_point": json.dumps(self._target_point.model_dump())
            if self._target_point
            else "null",
            "surface_range_m": str(obs.position.distance_to(self._target_point))
            if self._target_point
            else "none",
            "surface_stop_radius_m": str(self.surface_stop_radius_m),
            "arrival_ttl_s": str(self.arrival_ttl_s),
            "speed_mps": str(obs.velocity.norm()),
        }

    def _hold(self, ctx):
        self.arrival_holds += 1
        return self.envelope(
            ctx,
            DecisionKind.WAYPOINT,
            WaypointGoal(
                target=self._hold_position,
                target_label=self.target_label,
                tolerance_m=0.1,
                stop_at_target=False,
            ),
            0.8,
            note="rgbd arrival braking hold",
            extra=self._evidence(ctx.observation),
        )

    async def decide(self, ctx):
        obs = ctx.observation
        # No await in this branch: stop is evaluated against current odometry,
        # not against the older pose whose image initiated a model request.
        if self._hold_position is not None:
            if self._fresh(obs) and self._confirmations >= 2:
                near = obs.position.distance_to(self._target_point) <= self.surface_stop_radius_m
                if near and obs.velocity.norm() <= self.stop_speed_mps and self.arrival_enabled:
                    self.stop_outputs += 1
                    return self.envelope(
                        ctx,
                        DecisionKind.MISSION_DIRECTIVE,
                        MissionDirective(
                            label=ProgressLabel.STOP,
                            rationale="confirmed RGB-D surface arrival with low live speed",
                        ),
                        0.8,
                        note="rgbd arrival stop",
                        extra=self._evidence(obs),
                    )
                return self._hold(ctx)
            self._clear_arrival()  # TTL never renews from odometry or a hold command.

        assert self.services is not None and self.services.inference is not None
        backend = self.services.inference
        image = global_store().get(obs.rgb.uri) if obs.rgb else None
        stored_depth = global_store().get(obs.depth.uri) if obs.depth else None
        depth = np.array(stored_depth, copy=True) if stored_depth is not None else None
        if image is None:
            raise RuntimeError("arrival localization requires source RGB")
        encoded = backend.encode_image(image)
        native = await super().decide(ctx)
        prompt = LOCALIZE_PROMPT.format(target=self.localization_target)
        reply = await backend.invoke(
            InferenceRequest(
                model_id=self.model_id,
                role="policy",
                prompt_hash="spf:arrival-localization:v1",
                input_tokens=len(prompt) // 4,
                image_count=1,
                observation_seq=obs.seq,
                prompt=prompt,
                images=(encoded,),
                response_schema=LOCALIZE_SCHEMA,
            )
        )
        self.localization_calls += 1
        try:
            item = parse_localization(str(reply.payload or ""))
            point = (
                localized_point(obs, depth, item["box"], self.camera_pitch_rad)
                if item["visible"]
                else None
            )
        except (ValueError, TypeError):
            self.localization_errors += 1
            point = None
        self._update_target(obs, point)
        if (
            self.arrival_enabled
            and self._confirmations >= 2
            and point is not None
            and obs.position.distance_to(point) <= self.surface_stop_radius_m
        ):
            self._hold_position = obs.position
            return self._hold(ctx)
        # Restamp availability after BOTH charged calls; retain the source image time.
        return self.envelope(
            ctx,
            native.kind,
            native.payload,
            native.confidence,
            note="native SPF motion with separate arrival localization",
            extra={**native.provenance, **self._evidence(obs)},
        )

    def stats(self):
        return {
            **super().stats(),
            "arrival_localization_calls": float(self.localization_calls),
            "arrival_localization_errors": float(self.localization_errors),
            "arrival_holds": float(self.arrival_holds),
        }
