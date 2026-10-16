"""Whole simulator wiring with delayed scripted replies, not a model-quality test."""

import asyncio
import json
import time
from pathlib import Path

from uavlab.live_qwen.runner import fly

REPLY_DELAY_NS = 100_000_000


class DelayedWorker:
    def __init__(self):
        self.current = None
        self.last_id = -1
        self.cancelled = False

    def submit(self, item):
        self.current = item
        self.last_id = item.request_id
        self.cancelled = False

    def revoke(self):
        self.cancelled = True

    def poll(self, version, now=None):
        item = self.current
        if item is None or time.perf_counter_ns()-item.observed_ns < REPLY_DELAY_NS:
            return []
        self.current = None
        done = dict(kind="done", item=item, payload=dict(status="complete", error=None))
        if self.cancelled:
            return [done]
        if item.request.role == "pilot":
            return [dict(kind="action", item=item, payload=dict(index=0,
                         tokens=[1, 1, 1, 1], step_fru_m_yaw_rad=[0.2, 0, 0, 0],
                         ready_ns=now)), done]
        payload = {
            "planner": dict(steps=[dict(objective="Move forward one meter", target=[1, 0, 0, 0])]),
            "direction": dict(kind="relative", target=[1, 0, 0, 0], terminal=True),
            "monitor": dict(status="stop", reason="scripted test reply"),
        }[item.request.role]
        return [dict(kind="result", item=item, payload=(payload, 1)), done]


def test_complete_wall_clock_grid_run_with_delayed_scripted_worker(tmp_path):
    settings = json.loads(Path("configs/experiments/qwen_async_local.json").read_text())
    settings.update(flight_seconds=8, inference_kind="scripted test double",
                    latency_preflight=False)
    case = dict(id="fixture", seed=1061, instruction="Move forward one meter and stop",
                expected_delta=[1, 0, 0, 0])
    result = asyncio.run(fly(DelayedWorker(), case, settings, tmp_path / "fixture"))
    assert result["task_pass"], result
    assert result["actions_consumed"] > 1
    assert result["fresh_actions"]
    assert result["goal_authorizations"] == 1
    assert result["role_calls"]["planner"] == 1
    assert result["role_calls"]["direction"] == 1
    assert result["role_calls"]["monitor"] == 1
    assert result["control_ticks"] > result["actions_consumed"]
    assert result["collisions"] == 0
    assert not result["out_of_bounds"]
