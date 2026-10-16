"""Durable live-run evidence; model inputs and evaluator-only task scores are separate."""

import base64
import json
import math
from collections import Counter

from .goals import angle_error, relative_goal


class Evidence:
    def __init__(self, out):
        self.out = out
        out.mkdir(parents=True, exist_ok=False)
        self.events = []
        self.file = (out / "events.jsonl").open("w", encoding="utf-8")

    def __call__(self, row):
        row = dict(row)
        for index, image in enumerate(row.pop("images", ())):
            name = f"input_{row['request_id']}_{index}.png"
            (self.out / name).write_bytes(base64.b64decode(image))
            row.setdefault("image_files", []).append(name)
        self.events.append(row)
        self.file.write(json.dumps(row, allow_nan=False) + "\n")
        self.file.flush()

    def save(self, name, value):
        (self.out / name).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")

    def close(self):
        self.file.close()


def summarize(state, obs, mission_case, evidence, gaps):
    position, yaw = relative_goal(mission_case["expected_delta"], state.origin, state.settings)
    error = obs.position.distance_to(position)
    heading = abs(math.degrees(angle_error(yaw, obs.yaw_rad)))
    rows = evidence.events
    consumed = [r for r in rows if r["kind"] == "action_consumed"]
    valid = all(r["packet"]["ready_ns"] <= r["wall_ns"] < r["packet"]["expires_ns"]
                and r["until_ns"] <= r["packet"]["expires_ns"] for r in consumed)
    counts = Counter(r["role"] for r in rows if r["kind"] == "submitted")
    return dict(
        stopped=state.stopped, contract_failed=state.failed, endpoint_error_m=error,
        heading_error_deg=heading, final_speed_mps=obs.velocity.norm(),
        task_pass=state.stopped and error <= state.settings["position_m"]
        and heading <= state.settings["heading_deg"]
        and obs.velocity.norm() <= state.settings["stopped_mps"],
        role_calls=dict(counts), actions_consumed=len(consumed), fresh_actions=valid,
        goal_authorizations=sum(r["kind"] == "goal_authorized" for r in rows),
        control_ticks=len(gaps), max_tick_gap_s=max(gaps, default=0),
        timing_pass=max(gaps, default=0) <= state.settings["max_tick_gap_s"],
        simulated_seconds=obs.t_sim_ns / 1e9,
        scope="wall-paced rendered grid3d; not AirSim",
        inference_kind=state.settings.get("inference_kind", "real shared Qwen"),
    )
