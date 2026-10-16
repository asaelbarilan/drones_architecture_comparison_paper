import numpy as np
import pytest

from tests.test_live_qwen import ORIGIN_NS, observation
from tests.test_live_qwen import state as scheduler_fixture
from uavlab.contracts import CameraIntrinsics, SensorRef
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.grounding import capture_depth, grounded_direction, observed_range
from uavlab.live_qwen.mission_plan import accept_plan

state = scheduler_fixture


def test_box_drives_point_without_navigation_default():
    proposal = grounded_direction(dict(target_visible=True, box=[400, 0, 500, 300]))
    expected_point = (450, 150)
    assert (proposal["target"]["u"], proposal["target"]["v"]) == expected_point
    assert proposal["target"]["target_visible"] is True


@pytest.mark.parametrize("box", [[500, 0, 400, 300], [-1, 0, 500, 300],
                                 [True, 0, 500, 300], None])
def test_invalid_visible_box_cannot_authorize_motion(box):
    with pytest.raises(ValueError):
        grounded_direction(dict(target_visible=True, box=box))


def test_absent_target_does_not_create_background_waypoint(state):
    scheduler, rows = state
    scheduler.settings["goal_mode"] = "visual"
    scheduler.goal = None
    scheduler.accept_goal(dict(target_visible=False, box=None), observation(),
                          ORIGIN_NS, ORIGIN_NS)
    assert scheduler.goal is None and scheduler.hold_until > ORIGIN_NS
    assert rows[-1]["kind"] == "grounding_absent"


def test_visual_continue_refreshes_without_advancing_or_dropping_mission(state):
    scheduler, rows = state
    accept_plan(scheduler, dict(steps=[dict(objective="Approach red pillar", target="red pillar")]),
                ORIGIN_NS)
    mission = scheduler.mission.instruction
    scheduler.accept_monitor(dict(status="continue", reason="still far"),
                             observation(2), ORIGIN_NS)
    assert scheduler.goal is None and scheduler.step_index == 0
    assert scheduler.plan["target"] == "red pillar" and not scheduler.completed
    assert scheduler.mission.instruction == mission
    assert scheduler.next_role(observation(2), False) == "direction"
    assert any(row["kind"] == "visual_waypoint_refresh" for row in rows)


def test_continue_before_arrival_keeps_existing_waypoint(state):
    scheduler, _ = state
    accept_plan(scheduler, dict(steps=[dict(objective="Approach", target="red pillar")]), ORIGIN_NS)
    goal = scheduler.goal
    scheduler.accept_monitor(dict(status="continue", reason="move"), observation(), ORIGIN_NS)
    assert scheduler.goal is goal


@pytest.mark.parametrize("depth,accepted", [(1.0, True), (3.0, False), (float("inf"), False)])
def test_visual_completion_needs_fresh_finite_near_depth(state, depth, accepted):
    scheduler, rows = state
    scheduler.settings["goal_mode"] = "visual"
    accept_plan(scheduler, dict(steps=[dict(objective="Approach and stop", target="red pillar")]),
                ORIGIN_NS)
    obs = observation(2).model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri="ground-depth", digest="test")))
    global_store().put("ground-depth", np.full((16, 16), depth))
    scheduler.accept_monitor(dict(status="stop", reason="nearby"), obs, ORIGIN_NS)
    assert not scheduler.stopped and scheduler.visual_stop_pending
    scheduler.accept_goal(dict(target_visible=True, box=[400, 400, 600, 600]),
                          obs, ORIGIN_NS, ORIGIN_NS)
    assert scheduler.stopped is accepted
    assert any(r["kind"] == "visual_stop_verification" for r in rows)


def test_request_depth_snapshot_survives_frame_eviction():
    obs = observation().model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri="depth-to-evict", digest="test")))
    global_store().put(obs.depth.uri, np.ones((16, 16)))
    snapshot = capture_depth(obs)
    global_store().clear()
    proposal = grounded_direction(dict(target_visible=True, box=[400, 400, 600, 600]))
    assert observed_range(proposal, obs) is None
    assert observed_range(proposal, obs, snapshot) == 1.0
