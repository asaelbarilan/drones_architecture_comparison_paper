import asyncio
import math
from types import SimpleNamespace

import pytest

from uavlab.contracts import Vec3
from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.shared_qwen import SharedQwenInference
from uavlab.plugins.reasoning.shared_qwen_pilot import (
    parse_direction,
    parse_monitor,
    parse_plan,
    pilot_action,
    remaining_fru,
)


@pytest.mark.parametrize("yaw", [0, math.pi / 2, -math.pi / 2, math.pi])
def test_action_goal_frame_roundtrip(yaw):
    a = pilot_action([2.0, 1.0, 0.5, 0.2], yaw)
    goal = Vec3(
        x=a.velocity.x * a.duration_s, y=a.velocity.y * a.duration_s, z=a.velocity.z * a.duration_s
    )
    r = remaining_fru(goal, Vec3(x=0, y=0, z=0), yaw, yaw - 0.2)
    assert r == pytest.approx([2, 1, 0.5, math.degrees(0.2)])
    assert a.velocity.norm() <= 2.000001
    assert a.yaw_rate_rps * a.duration_s == pytest.approx(-0.2)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True])
def test_invalid_action(value):
    with pytest.raises(ValueError):
        pilot_action([value, 0, 0, 0], 0)


def test_role_contracts_reject_ambiguity():
    with pytest.raises(ValueError):
        parse_plan({"objective": "go", "target": "red", "extra": 1})
    with pytest.raises(ValueError):
        parse_direction(dict(u=500, v=500, travel_m=float("nan"), target_visible=False, box=None))
    with pytest.raises(ValueError):
        parse_monitor(dict(status="success", reason="yes"))


def test_one_backend_four_roles_and_measured_clock():
    b = SharedQwenInference("unused")
    modes, charges = [], []

    def run(r):
        b.load_count = 1
        modes.append(r.role)
        return "ok", 1

    async def sleep(ns):
        charges.append(ns)

    b._run = run
    b.bind_runtime(SimpleNamespace(clock=SimpleNamespace(sleep_ns=sleep)))

    async def calls():
        for role in ("planner", "direction", "monitor", "pilot", "planner"):
            await b.invoke(InferenceRequest(model_id=b.model_id, role=role, prompt_hash="test"))

    asyncio.run(calls())
    assert len(charges) == 5 and all(x > 0 for x in charges)
    assert modes == ["planner", "direction", "monitor", "pilot", "planner"]
    assert b.stats()["shared_base_load_count"] == 1


@pytest.mark.parametrize(
    "distance,heading,expected_stop", [(0, 0, True), (2, 0, False), (0, 0.3, False)]
)
def test_monitor_arrival_before_goal_refresh(distance, heading, expected_stop):
    from PIL import Image

    from uavlab.core.frame_store import global_store
    from uavlab.plugins.reasoning.shared_qwen_pilot import SharedQwenPilot

    global_store().put("d132-test", Image.new("RGB", (32, 32)))
    obs = SimpleNamespace(
        rgb=SimpleNamespace(uri="d132-test"),
        intrinsics=object(),
        seq=0,
        position=Vec3(x=0, y=0, z=1),
        velocity=Vec3(x=0, y=0, z=0),
        yaw_rad=0,
    )
    ctx = SimpleNamespace(
        t_sim_ns=0,
        observation=obs,
        last_routing_feedback=None,
        mission=SimpleNamespace(instruction="reach tower"),
    )
    p = SharedQwenPilot()
    p._plan = dict(objective="reach tower", target="tower")
    p._goal = Vec3(x=distance, y=0, z=1)
    p._goal_yaw = heading
    p.services = SimpleNamespace(inference=object())
    p.envelope = lambda ctx, kind, payload, *a, **kw: payload
    calls = []

    async def call(ctx, role, prompt, image=None):
        calls.append(role)
        if role == "direction":
            return dict(u=500, v=500, travel_m=2, target_visible=False, box=None)
        return dict(status="stop", reason="arrived")

    p._call = call
    result = asyncio.run(p.decide(ctx))
    assert hasattr(result, "label") == expected_stop
    assert calls == ["direction", "monitor"]
    assert p._goal == Vec3(x=distance, y=0, z=1)


def test_adapter_restored_when_language_role_fails():
    from contextlib import contextmanager, nullcontext

    b = SharedQwenInference("unused")

    class Model:
        enabled = True

        @contextmanager
        def disable_adapter(self):
            self.enabled = False
            try:
                yield
            finally:
                self.enabled = True

        def generate(self, **kw):
            assert not self.enabled
            raise ValueError("deliberate failure")

    b.model = Model()
    b._load = lambda: None
    b._chat_batch = lambda r: {}
    b.torch = SimpleNamespace(inference_mode=nullcontext)
    b.api = SimpleNamespace(cuda=lambda x: x)
    b.processor = SimpleNamespace(tokenizer=SimpleNamespace(pad_token_id=0))
    with pytest.raises(ValueError, match="deliberate"):
        b._run(InferenceRequest(model_id=b.model_id, role="planner", prompt_hash="test"))
    assert b.model.enabled


def test_development_profile_loads():
    from uavlab.core.compose import load_architecture

    c = load_architecture("shared_qwen_vla_dev")
    assert c.policy.name == "shared_qwen_pilot"
    assert c.inference.name == "shared_qwen_vla"
    assert c.shield.name == "simple_collision"
