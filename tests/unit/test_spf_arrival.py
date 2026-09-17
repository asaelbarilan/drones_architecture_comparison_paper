"""Arrival interface behavior; no real inference."""

import ast
import asyncio
import inspect
import json

import numpy as np
import pytest
from PIL import Image

from uavlab.contracts import (
    CameraIntrinsics,
    DecisionKind,
    MemorySnapshot,
    MissionSpec,
    ObservationPacket,
    PerceptionState,
    SensorRef,
    TaskFamily,
    Vec3,
)
from uavlab.core.clock import SimClock
from uavlab.core.compose import load_architecture
from uavlab.core.event_log import EventLog
from uavlab.core.feature_cache import FeatureCache
from uavlab.core.frame_store import global_store
from uavlab.core.services import RuntimeServices, bind
from uavlab.interfaces import DecisionContext, InferenceResult
from uavlab.plugins.reasoning import spf_arrival
from uavlab.plugins.reasoning.spf_arrival import (
    SPFRGBDArrivalPolicy,
    localized_point,
    parse_localization,
)

MISSION = MissionSpec(
    mission_id="arrival-test",
    instruction="Fly to the red pillar and stop within 2 metres.",
    task_family=TaskFamily.SEMANTIC_GOAL_NAV,
)
VISIBLE = {"evidence": "red pillar", "visible": True, "box": [400, 400, 600, 600]}
ABSENT = {"evidence": "no red pillar", "visible": False, "box": [0, 0, 0, 0]}


def ctx(t=0, seq=1, x=0, speed=0.6, depth=0.8):
    rgb_uri, depth_uri = f"test-rgb-{seq}", f"test-depth-{seq}"
    global_store().put(rgb_uri, Image.new("RGB", (101, 101), "red"))
    global_store().put(depth_uri, np.full((101, 101), depth))
    obs = ObservationPacket(
        seq=seq,
        t_sim_ns=int(t * 1e9),
        t_wall_ns=0,
        position=Vec3(x=x, y=0, z=3),
        velocity=Vec3(x=speed, y=0, z=0),
        yaw_rad=0,
        rgb=SensorRef(kind="rgb", uri=rgb_uri, digest="rgb"),
        depth=SensorRef(kind="depth", uri=depth_uri, digest="depth"),
        intrinsics=CameraIntrinsics(width=101, height=101, fx=50, fy=50, cx=50, cy=50),
        privileged={"goal": (1000, 1000, 1000)},
    )
    return DecisionContext(
        mission=MISSION,
        observation=obs,
        perception=PerceptionState(observation_seq=seq, t_sim_ns=obs.t_sim_ns),
        memory=MemorySnapshot(observation_seq=seq, t_sim_ns=obs.t_sim_ns),
        t_sim_ns=obs.t_sim_ns,
        t_wall_ns=0,
        episode_id="arrival-test",
    )


class Model:
    def __init__(self, localization=VISIBLE, invalidate_store=False):
        self.localization = localization
        self.requests = []
        self.invalidate_store = invalidate_store

    def encode_image(self, image):
        return "encoded-rgb"

    async def invoke(self, request):
        self.requests.append(request)
        if self.invalidate_store:
            global_store().clear()
        reply = (
            self.localization
            if "arrival-localization" in request.prompt_hash
            else {"u": 500, "v": 500, "distance": 1}
        )
        return InferenceResult(payload=json.dumps(reply), output_tokens=10, latency_ns=0)


def policy(model=None):
    p = SPFRGBDArrivalPolicy(camera_pitch_rad=0)
    m = model or Model()
    bind(
        p,
        RuntimeServices(
            clock=SimClock(),
            log=EventLog("arrival-test", None),
            feature_cache=FeatureCache(),
            inference=m,
        ),
    )
    p.reset(MISSION, 1)
    return p, m


def decide(p, c):
    return asyncio.run(p.decide(c))


def test_localization_then_brake_then_fresh_low_speed_stop():
    p, m = policy()
    assert decide(p, ctx()).kind is DecisionKind.WAYPOINT
    hold = decide(p, ctx(t=2, seq=2))
    assert hold.provenance["note"] == "rgbd arrival braking hold"
    assert p._confirmations == 2
    assert decide(p, ctx(t=2.5, seq=3, speed=0.4)).kind is DecisionKind.WAYPOINT
    stop = decide(p, ctx(t=3, seq=4, speed=0.1))
    assert stop.kind is DecisionKind.MISSION_DIRECTIVE
    assert stop.source_observation_seq == 4
    assert stop.provenance["arrival_source_seq"] == "2"
    assert stop.provenance["arrival_source_t_ns"] == "2000000000"
    assert len(m.requests) == 4  # No new model call can make this STOP stale.


def test_far_target_never_stops_even_when_native_labels_say_near():
    p, _ = policy()
    for t in range(4):
        out = decide(p, ctx(t=t, seq=t + 1, depth=3.4, speed=0))
        assert out.kind is DecisionKind.WAYPOINT
        assert out.provenance["note"] != "rgbd arrival braking hold"


@pytest.mark.parametrize("depth", [float("inf"), float("nan"), 0, -1, 40])
def test_invalid_depth_does_not_confirm(depth):
    p, _ = policy()
    for i in range(2):
        assert decide(p, ctx(t=i, seq=i + 1, depth=depth)).kind is DecisionKind.WAYPOINT
    assert p._confirmations == 0 and p._hold_position is None


def test_absence_and_different_target_clear_confirmation():
    p, m = policy()
    decide(p, ctx())
    m.localization = ABSENT
    decide(p, ctx(t=1, seq=2))
    assert p._confirmations == 0
    m.localization = VISIBLE
    decide(p, ctx(t=2, seq=3))
    decide(p, ctx(t=3, seq=4, x=3))
    assert p._confirmations == 1 and p._hold_position is None


def test_same_frame_cannot_confirm_twice():
    p, _ = policy()
    c = ctx()
    decide(p, c)
    decide(p, c)
    assert p._confirmations == 1 and p._hold_position is None


def test_hold_uses_live_position_and_speed_not_old_arrival():
    p, _ = policy()
    decide(p, ctx())
    decide(p, ctx(t=2, seq=2))
    assert decide(p, ctx(t=3, seq=3, x=5, speed=0)).kind is DecisionKind.WAYPOINT
    assert decide(p, ctx(t=3.5, seq=4, speed=0.6)).kind is DecisionKind.WAYPOINT


def test_track_expires_and_hold_does_not_refresh_timestamp():
    p, m = policy()
    decide(p, ctx())
    decide(p, ctx(t=2, seq=2))
    decide(p, ctx(t=7, seq=3, speed=0.6))
    assert p._target_t_ns == 2_000_000_000
    m.localization = ABSENT
    out = decide(p, ctx(t=8.01, seq=4, speed=0))
    assert out.kind is DecisionKind.WAYPOINT and p._hold_position is None
    assert p._confirmations == 0


def test_source_buffers_survive_inference_eviction():
    p, _ = policy(Model(invalidate_store=True))
    decide(p, ctx())
    assert p._confirmations == 1  # Depth copied and RGB encoded before either await.


def test_unprojection_uses_intrinsics_and_yaw():
    c = ctx()
    point = localized_point(c.observation, np.full((101, 101), 2.0), [400, 400, 599, 599], 0)
    assert point.x == pytest.approx(2) and point.y == pytest.approx(0, abs=0.003)
    rotated = c.observation.model_copy(update={"yaw_rad": np.pi / 2})
    point = localized_point(rotated, np.full((101, 101), 2.0), [400, 400, 599, 599], 0)
    assert point.y == pytest.approx(2) and point.x == pytest.approx(0, abs=0.003)


@pytest.mark.parametrize(
    "bad",
    [
        {"visible": True, "evidence": "x", "box": [0, 0, 0, 0]},
        {"visible": False, "evidence": "x", "box": [1, 2, 3, 4]},
        {"visible": 1, "evidence": "x", "box": [1, 2, 3, 4]},
    ],
)
def test_strict_box_parser(bad):
    with pytest.raises(ValueError):
        parse_localization(json.dumps(bad))


def test_named_configs_keep_native_and_c3_difference():
    a, b = [load_architecture(f"{f}_spf_rgbd_arrival_qwen4_dev") for f in ["c2", "c3"]]
    assert a.policy == b.policy and a.monitor is None and b.monitor is None
    assert a.verifier is None and b.verifier.name == "semantic_geometric"
    assert load_architecture("c2_spf_qwen4_current_dev").policy.name == "spf_waypoint"
    attrs = {
        n.attr
        for n in ast.walk(ast.parse(inspect.getsource(spf_arrival)))
        if isinstance(n, ast.Attribute)
    }
    assert not attrs & {"privileged", "semantic_hits", "detections", "goal", "status"}


def test_availability_includes_both_calls():
    p, model = policy()
    invoke = model.invoke

    async def delayed(request):
        p.services.clock._now += 1_000_000_000  # Controlled inference delay fixture.
        return await invoke(request)

    model.invoke = delayed
    envelope = decide(p, ctx(depth=3.4))
    assert envelope.source_t_sim_ns == 0
    assert envelope.produced_t_sim_ns == 2_000_000_000
    assert envelope.valid_until_t_sim_ns == 4_000_000_000


def test_missing_depth_fails_closed_and_reset_clears_track():
    p, _ = policy()
    c = ctx()
    global_store().clear()
    global_store().put(c.observation.rgb.uri, Image.new("RGB", (101, 101), "red"))
    assert decide(p, c).kind is DecisionKind.WAYPOINT
    assert p._confirmations == 0
    decide(p, ctx(t=1, seq=2))
    decide(p, ctx(t=2, seq=3))
    assert p._hold_position is not None
    p.reset(MISSION, 2)
    assert p._hold_position is None and p._confirmations == 0
