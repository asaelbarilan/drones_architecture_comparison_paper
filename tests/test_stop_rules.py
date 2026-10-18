from types import SimpleNamespace

import numpy as np
import pytest

from tests.test_live_qwen import ORIGIN_NS, observation
from tests.test_live_qwen import state as scheduler_fixture
from uavlab.contracts import CameraIntrinsics, SensorRef, Vec3, s_to_ns
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.grounding import NEAR_OBJECT_M
from uavlab.live_qwen.mission_plan import accept_plan, parse_steps
from uavlab.live_qwen.stop_rules import aim_standoff, near_limit, object_below

state = scheduler_fixture
TTL_S = 15
HOLD_S = 2.0


def test_planner_may_state_standoff_and_hold():
    steps = parse_steps(dict(steps=[dict(objective="Hover 1 m before the pillar for 2 s",
                                         target="red pillar", standoff_m=1, hold_s=HOLD_S)]))
    assert steps[0]["standoff_m"] == 1 and steps[0]["hold_s"] == HOLD_S


@pytest.mark.parametrize("extra", [dict(standoff_m=0.1), dict(hold_s=-1), dict(hold_s="2"),
                                   dict(speed=3)])
def test_invalid_or_unknown_step_fields_rejected(extra):
    with pytest.raises(ValueError):
        parse_steps(dict(steps=[dict(objective="Approach", target="red pillar", **extra)]))


@pytest.mark.parametrize("plan,limit,aim", [
    (dict(target="red pillar"), NEAR_OBJECT_M, NEAR_OBJECT_M - 0.25),
    (dict(target="red pillar", standoff_m=1.0), 1.25, 1.0),
    (dict(target="red pillar", standoff_m=2.0), NEAR_OBJECT_M, NEAR_OBJECT_M - 0.25),
])
def test_stated_standoff_only_tightens(plan, limit, aim):
    holder = SimpleNamespace(plan=plan)
    assert near_limit(holder) == pytest.approx(limit)
    assert aim_standoff(holder) == pytest.approx(aim)


def memory_state(target="overturned vehicle", seen_s=0.0):
    return SimpleNamespace(
        plan=dict(target="overturned vehicle"), settings=dict(cognition_ttl_s=TTL_S,
                                                              stopped_mps=0.2),
        object_memory=dict(position=Vec3(x=12, y=4, z=0.9), target=target,
                           seen_ns=ORIGIN_NS + s_to_ns(seen_s)))


def above(x, y, speed=0.0):
    return SimpleNamespace(position=Vec3(x=x, y=y, z=3.0),
                           velocity=Vec3(x=speed, y=0, z=0))


@pytest.mark.parametrize("holder,obs,expected", [
    (memory_state(), above(12.4, 3.8), True),                     # D-157 vehicle end pose
    (memory_state(target="red pillar"), above(12.4, 3.8), False),  # different object
    (memory_state(seen_s=-30), above(12.4, 3.8), False),           # stale estimate
    (memory_state(), above(9.8, 3.5), False),                      # still 2.3 m away
    (memory_state(), above(12.4, 3.8, speed=1.0), False),          # still moving
])
def test_object_below_means_arrival_only_when_recent_close_and_still(holder, obs, expected):
    assert object_below(holder, obs, ORIGIN_NS) is expected


def depth_obs(depth, uri):
    global_store().put(uri, np.full((16, 16), depth))
    return observation(2).model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri=uri, digest="test")))


def test_requested_hold_delays_finish_until_hold_time_passes(state):
    scheduler, rows = state
    scheduler.settings.update(goal_mode="visual", camera_pitch_rad=-0.1)
    accept_plan(scheduler, dict(steps=[dict(objective="Hover 1 m before it, hold 2 s",
                                            target="red pillar", standoff_m=1, hold_s=HOLD_S)]),
                ORIGIN_NS)
    obs = depth_obs(1.1, "hold-depth")
    # Fresh near grounding first (sets the hold goal and asks the monitor), then the
    # monitor answers "hold", as in the D-157 approach_hover run.
    scheduler.accept_goal(dict(target_visible=True, box=[400, 400, 600, 600]),
                          obs, ORIGIN_NS, ORIGIN_NS)
    assert scheduler.monitor_reason is not None
    scheduler.accept_monitor(dict(status="hold", reason="ready to hold"), obs, ORIGIN_NS)
    assert scheduler.hold_started is not None and not scheduler.stopped
    scheduler.check_hold(obs, ORIGIN_NS + s_to_ns(HOLD_S / 2))
    assert not scheduler.stopped
    scheduler.check_hold(obs, ORIGIN_NS + s_to_ns(HOLD_S))
    assert scheduler.stopped
    assert any(r["kind"] == "hold_started" for r in rows)


def test_object_out_of_view_below_drone_completes_step(state):
    scheduler, rows = state
    scheduler.settings.update(goal_mode="visual", camera_pitch_rad=-0.1)
    accept_plan(scheduler, dict(steps=[dict(objective="Hover above the vehicle",
                                            target="overturned vehicle")]), ORIGIN_NS)
    obs = depth_obs(1.0, "below-depth")
    scheduler.object_memory = dict(position=Vec3(x=2.3, y=0.2, z=0.9),
                                   target="overturned vehicle", seen_ns=ORIGIN_NS)
    scheduler.accept_goal(dict(target_visible=False, box=None), obs, ORIGIN_NS, ORIGIN_NS)
    assert scheduler.stopped
    assert any(r["kind"] == "object_below_completion" for r in rows)


@pytest.mark.parametrize("objective,expected", [
    ("Approach the red pillar and hover about 1 metre before it on your approach side.",
     dict(standoff_m=1.0)),
    ("Hold for 2 continuous seconds", dict(hold_s=2.0)),
    ("Fly to the red pillar and stop within 2 metres.", {}),           # a limit, not a standoff
    ("Hover about 9 metres from it", {}),                              # outside accepted range
    ("Use the threshold for 5 seconds", {}),                           # not the word "hold"
])
def test_stated_numbers_read_from_step_text(objective, expected):
    step = parse_steps(dict(steps=[dict(objective=objective, target="red pillar")]))[0]
    assert {k: step[k] for k in ("standoff_m", "hold_s") if k in step} == expected


def test_monitor_hold_counts_as_stop_when_fresh_near_and_still(state):
    scheduler, _ = state
    scheduler.settings.update(goal_mode="visual", camera_pitch_rad=-0.1)
    accept_plan(scheduler, dict(steps=[dict(objective="Approach the red pillar and hover",
                                            target="red pillar")]), ORIGIN_NS)
    obs = depth_obs(1.1, "plain-hold-depth")
    scheduler.accept_goal(dict(target_visible=True, box=[400, 400, 600, 600]),
                          obs, ORIGIN_NS, ORIGIN_NS)
    scheduler.accept_monitor(dict(status="hold", reason="stay"), obs, ORIGIN_NS)
    assert scheduler.stopped
