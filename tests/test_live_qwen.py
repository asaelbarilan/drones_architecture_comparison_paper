import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from uavlab.contracts import ControlCommand, ObservationPacket, SensorRef, Vec3, s_to_ns
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.control import LiveControl
from uavlab.live_qwen.goals import Goal, relative_goal
from uavlab.live_qwen.runner import advance, mission_spec
from uavlab.live_qwen.scheduler import GoalScheduler

ORIGIN_NS = s_to_ns(100)


class ManualWorker:
    def __init__(self):
        self.current = None
        self.last_id = -1
        self.events = []
        self.calls = []
        self.revocations = 0

    def submit(self, item):
        assert self.current is None
        self.current = item
        self.calls.append(item)
        self.last_id = item.request_id

    def revoke(self):
        self.revocations += 1

    def poll(self, version, now=None):
        events, self.events = self.events, []
        if events:
            self.current = None
        return events

    def finish(self, payload):
        item = self.current
        self.events = [dict(kind="result", item=item, payload=(payload, 1)),
                       dict(kind="done", item=item, payload=dict(status="complete", error=None))]


def observation(x=0, yaw=0, speed=0):
    global_store().put("live-test", Image.new("RGB", (16, 16)))
    return ObservationPacket(seq=1, t_sim_ns=0, t_wall_ns=ORIGIN_NS,
                              position=Vec3(x=x, y=0, z=3), velocity=Vec3(x=speed, y=0, z=0),
                              yaw_rad=yaw,
                              rgb=SensorRef(kind="rgb", uri="live-test", digest="test"))


@pytest.fixture
def state():
    settings = json.loads(Path("configs/experiments/qwen_async_local.json").read_text())
    rows = []
    value = GoalScheduler(ManualWorker(), mission_spec(settings["missions"][0], settings),
                          settings, rows.append)
    value.origin = observation()
    value.plan = dict(objective="Move forward 2 meters.", target="numeric position")
    value.goal = Goal(1, Vec3(x=2, y=0, z=3), 0, True, ORIGIN_NS+s_to_ns(45), 1)
    value.version = 1
    value.last_monitor = value.progress_at = ORIGIN_NS
    return value, rows


def test_persistent_goal_reuses_authorization_for_multiple_pilot_calls(state):
    state, rows = state
    initial = state.goal
    for index in range(3):
        now = ORIGIN_NS+s_to_ns(index)
        state.update(observation(x=index/10), now, now, False)
        assert state.worker.current.request.role == "pilot"
        state.worker.finish({})
    assert all(work.request.role == "pilot" for work in state.worker.calls)
    assert state.goal is initial
    assert not any(row["kind"] == "goal_authorized" for row in rows)


def test_replan_numeric_goal_is_anchored_to_episode_origin(state):
    state, _ = state
    payload = dict(kind="relative", target=[2, 0, 0, 0], terminal=True)
    state.accept_goal(payload, observation(x=1), ORIGIN_NS, ORIGIN_NS)
    assert state.goal.position.x == payload["target"][0]
    state.accept_goal(payload, observation(x=1.5), ORIGIN_NS, ORIGIN_NS)
    assert state.goal.position.x == payload["target"][0]


def test_arrival_requires_heading_and_rejects_early_monitor_stop(state):
    state, rows = state
    state.accept_monitor(dict(status="stop", reason="looks done"), observation(), ORIGIN_NS)
    assert not state.stopped
    assert rows[-1]["kind"] == "stop_rejected"
    obs = observation(x=2, yaw=1)
    assert not state.goal.arrived(obs, state.settings)
    state.accept_monitor(dict(status="stop", reason="done"), obs, ORIGIN_NS)
    assert not state.stopped
    state.accept_monitor(dict(status="stop", reason="done"), observation(x=2), ORIGIN_NS)
    assert state.stopped


def test_arrival_cancels_inflight_pilot_then_runs_monitor(state):
    state, _ = state
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    now = ORIGIN_NS+s_to_ns(3)
    state.update(observation(x=2), now, now, True)
    assert state.monitor_reason == "arrival"
    assert state.worker.revocations == 1
    assert not state.buffer.queue
    state.worker.events = [dict(kind="done", item=state.worker.current,
                                payload=dict(status="cancelled", error="revoked"))]
    state.update(observation(x=2), now, now, False)
    assert state.worker.current.request.role == "monitor"


def test_stale_cognitive_pose_cannot_authorize_goal(state):
    state, rows = state
    state.goal = None
    state.submit("direction", observation(), ORIGIN_NS)
    state.worker.finish(dict(kind="relative", target=[2, 0, 0, 0], terminal=True))
    state.update(observation(x=1), ORIGIN_NS, ORIGIN_NS, False)
    assert state.goal is None
    assert any(r["kind"] == "contract_failure" and "pose drift" in r["error"] for r in rows)


def test_expired_goal_clears_actions_and_returns_to_planner(state):
    state, _ = state
    state.goal = replace(state.goal, expires_ns=ORIGIN_NS)
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    assert state.goal is None
    assert state.worker.current.request.role == "planner"


def test_controller_hovers_during_cognition_without_waiting(state):
    state, _ = state
    state.request_monitor("external obstacle", ORIGIN_NS)
    control = LiveControl(state, state.settings, 1061)
    command = control.tick(observation(), ORIGIN_NS, ORIGIN_NS)
    assert command.is_hold
    assert state.worker.current.request.role == "monitor"
    command = control.tick(observation(), ORIGIN_NS, ORIGIN_NS+s_to_ns(1))
    assert command.is_hold


def queued_action(state, now):
    state.buffer.begin(0, state.version)
    packet = dict(request_id=0, goal_version=state.version, index=0,
                  observation_seq=1, source_t_sim_ns=0, observed_ns=now,
                  ready_ns=now, expires_ns=now+s_to_ns(1.5), tokens=[1, 1, 1, 1],
                  step_fru_m_yaw_rad=[0.2, 0, 0, 0])
    state.buffer.append(packet)
    return packet


def test_revoke_stops_active_command_and_discards_unexecuted_suffix(state):
    state, _ = state
    control = LiveControl(state, state.settings, 1061)
    packet = queued_action(state, ORIGIN_NS)
    assert not control.tick(observation(), ORIGIN_NS, ORIGIN_NS).is_hold
    state.buffer.append(dict(packet, index=1))
    state.request_monitor("obstacle", ORIGIN_NS)
    assert control.tick(observation(), ORIGIN_NS, ORIGIN_NS).is_hold
    assert not state.buffer.queue


def test_later_action_can_append_while_first_is_executing(state):
    state, rows = state
    control = LiveControl(state, state.settings, 1061)
    packet = queued_action(state, ORIGIN_NS)
    control.tick(observation(), ORIGIN_NS, ORIGIN_NS)
    state.buffer.append(dict(packet, index=1))
    now = ORIGIN_NS+s_to_ns(0.6)
    command = control.tick(observation(x=0.1), now, now)
    assert not command.is_hold
    consumed = [r["packet"]["index"] for r in rows if r["kind"] == "action_consumed"]
    assert consumed == [0, 1]


def test_real_shield_intervenes_and_requests_monitor(state):
    state, rows = state
    control = LiveControl(state, state.settings, 1061)
    queued_action(state, ORIGIN_NS)
    obstacle = observation().model_copy(update=dict(free_range_m=0.1))
    assert control.tick(obstacle, ORIGIN_NS, ORIGIN_NS).is_hold
    assert state.monitor_reason.startswith("shield intervention")
    assert any(r["kind"] == "shield" for r in rows)


def test_periodic_monitor_preempts_pilot_but_keeps_anchored_goal(state):
    state, _ = state
    original = state.goal
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    now = ORIGIN_NS+s_to_ns(state.settings["monitor_interval_s"])
    state.progress_at = now
    state.update(observation(x=0.5), now, now, True)
    assert state.monitor_reason == "periodic scene check"
    assert state.goal is original
    assert state.worker.revocations == 1


def test_cognitive_expiry_is_failure_not_silent_success(state):
    state, rows = state
    state.goal = None
    state.submit("direction", observation(), ORIGIN_NS)
    work = state.worker.current
    state.worker.events = [dict(kind="done", item=work,
                                payload=dict(status="cancelled", error="expired"))]
    state.update(observation(), work.expires_ns, work.expires_ns, False)
    assert state.failures == 1
    assert state.goal is None
    assert any(r["kind"] == "contract_failure" for r in rows)


def test_monitor_stop_at_intermediate_goal_advances_instead_of_ending_mission(state):
    state, _ = state
    state.goal = replace(state.goal, terminal=False)
    state.accept_monitor(dict(status="stop", reason="at local point"), observation(x=2), ORIGIN_NS)
    assert not state.stopped
    assert state.goal is None and state.plan is None
    assert len(state.completed) == 1
    assert "advance mission" in state.feedback


def test_physics_advance_splits_at_command_expiry_even_after_late_tick():
    class Env:
        def __init__(self):
            self.rows = []

        async def step(self, command, dt):
            self.rows.append((command.is_hold, dt))

    env = Env()
    expiry, elapsed = s_to_ns(0.03), s_to_ns(0.12)
    command = ControlCommand(t_sim_ns=0, velocity=Vec3(x=1, y=0, z=0), expires_t_sim_ns=expiry)
    asyncio.run(advance(env, command, 0, elapsed))
    assert sum(dt for hold, dt in env.rows if not hold) == expiry
    assert sum(dt for _, dt in env.rows) == elapsed
    assert env.rows[-1][0]


@pytest.mark.parametrize("delta", [[False, 0, 0, 0], [float("nan"), 0, 0, 0], [100, 0, 0, 0]])
def test_model_goal_validation_rejects_nonfinite_or_unbounded(state, delta):
    state, _ = state
    with pytest.raises(ValueError):
        relative_goal(delta, observation(), state.settings)
