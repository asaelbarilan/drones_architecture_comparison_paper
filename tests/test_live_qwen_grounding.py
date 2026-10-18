import numpy as np
import pytest

from tests.test_live_qwen import ORIGIN_NS, observation
from tests.test_live_qwen import state as scheduler_fixture
from uavlab.contracts import CameraIntrinsics, SensorRef, Vec3, s_to_ns
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.goals import Goal, visual_goal
from uavlab.live_qwen.grounding import (NEAR_OBJECT_M, capture_depth, grounded_direction,
                                        observed_range)
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


@pytest.mark.parametrize("depth,travel", [(12.0, 10.0), (6.0, 4.75), (2.5, 1.25),
                                          (float("inf"), 1.0)])
def test_visual_waypoint_uses_depth_up_to_local_goal_bound(state, depth, travel):
    scheduler, _ = state
    scheduler.pending_depth = np.full((16, 16), depth)
    obs = observation().model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri="retained-depth", digest="test")))
    proposal = scheduler.prepare_visual_goal(dict(target_visible=True, box=[400, 400, 600, 600]),
                                             obs, ORIGIN_NS, ORIGIN_NS)
    assert proposal["target"]["travel_m"] == pytest.approx(travel)
    assert not scheduler.stopped


def test_visual_waypoint_just_outside_near_range_is_not_reached_on_issue(state):
    # D150 search repeat: range 1.57 m gave a 0.25 m waypoint, inside the 0.5 m
    # arrival tolerance, so it was "reached" at once and the drone never closed in.
    scheduler, _ = state
    scheduler.pending_depth = np.full((16, 16), 1.57)
    obs = observation().model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri="retained-depth", digest="test")))
    proposal = scheduler.prepare_visual_goal(dict(target_visible=True, box=[400, 400, 600, 600]),
                                             obs, ORIGIN_NS, ORIGIN_NS)
    travel = proposal["target"]["travel_m"]
    assert travel > scheduler.settings["position_m"]
    assert 1.57 - travel + scheduler.settings["position_m"] < NEAR_OBJECT_M


def test_visual_waypoint_from_two_metres_stops_short_of_losing_view(state):
    # D153 long-waypoint run: from 2.11 m the old 0.75 m aim flew close enough
    # that the pillar left the camera and the drone froze on target_lost.
    scheduler, _ = state
    scheduler.pending_depth = np.full((16, 16), 2.11)
    obs = observation().model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri="retained-depth", digest="test")))
    proposal = scheduler.prepare_visual_goal(dict(target_visible=True, box=[400, 400, 600, 600]),
                                             obs, ORIGIN_NS, ORIGIN_NS)
    end_range = 2.11 - proposal["target"]["travel_m"]
    assert 1.0 <= end_range <= NEAR_OBJECT_M


def test_no_periodic_monitor_mid_visual_leg(state):
    scheduler, rows = state
    accept_plan(scheduler, dict(steps=[dict(objective="Fly to the red pillar.",
                                            target="red pillar")]), ORIGIN_NS)
    scheduler.goal = Goal(scheduler.version, Vec3(x=10, y=0, z=3), 0, True,
                          ORIGIN_NS+s_to_ns(45), 1)
    now = ORIGIN_NS+s_to_ns(scheduler.settings["monitor_interval_s"])
    scheduler.progress_at = now
    scheduler.check_events(observation(x=5), now)
    assert scheduler.monitor_reason is None
    assert not any(r["kind"] == "motion_revoked" for r in rows)


@pytest.mark.parametrize("mode", ["ray", "hold"])
def test_visual_goal_altitude_mode(mode):
    obs = observation().model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8)))
    settings = dict(max_goal_m=10, camera_pitch_rad=-0.1, min_altitude_m=0.5,
                    visual_altitude=mode)
    # Box centre high in the frame, as for a tall pillar seen from its mid-height.
    position, _ = visual_goal(dict(u=500, v=200, travel_m=8.0, target_visible=True,
                                   box=[450, 100, 550, 300]), obs, settings)
    if mode == "hold":
        assert position.z == pytest.approx(obs.position.z)
    else:
        assert position.z > obs.position.z + 1.0
    assert position.x > obs.position.x + 7.0
