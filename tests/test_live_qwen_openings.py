"""D-174 H5 measured openings from the range fan (CPU only)."""

import math

import pytest

from tests.test_live_qwen import observation
from uavlab.live_qwen.openings import find_openings, named_opening, range_facts, through_point

WALL_X, FAR_M, RAYS = 8.0, 25.0, 24
GAP_BEARING = 22.5
EDGE = 1e-6


def wall_scan(left_blocked=False):
    """A wall at x=8 with gaps at y in (2, 8) and (-8, -2), as the drone's 24-ray fan sees it."""
    segments = [(-16, -8), (-2, 2), (8, 16)] + ([(2, 8)] if left_blocked else [])
    bearings, ranges = [], []
    for i in range(RAYS):
        bearing = -math.pi + 2 * math.pi * i / RAYS
        bearings.append(bearing)
        distance = FAR_M
        if abs(bearing) < math.pi / 2:
            y = WALL_X * math.tan(bearing)
            if any(lo - EDGE <= y <= hi + EDGE for lo, hi in segments):
                distance = WALL_X / math.cos(bearing)
        ranges.append(distance)
    return observation().model_copy(update=dict(range_rays=tuple(ranges),
                                                ray_bearings_rad=tuple(bearings)))


def test_both_gaps_are_found_on_their_sides():
    gaps = [o for o in find_openings(wall_scan()) if o["kind"] == "opening"]
    assert sorted(o["side"] for o in gaps) == ["left", "right"]
    left = named_opening(gaps, "left opening")
    assert left["bearing_deg"] == pytest.approx(GAP_BEARING) and left["distance_m"] == WALL_X


def test_a_blocked_gap_disappears_and_is_reported_as_walled():
    facts = range_facts(wall_scan(left_blocked=True))
    assert [o["side"] for o in facts["measured_openings"] if o["kind"] == "opening"] == ["right"]
    assert "left" in facts["walled_sides_without_opening"]
    assert named_opening(facts["measured_openings"], "left opening") is None


def test_pass_point_goes_through_and_beyond_the_named_gap():
    gap = named_opening(find_openings(wall_scan()), "right gap")
    point, heading = through_point(gap, observation(), 2.0)
    assert point.x > WALL_X and point.y < 0 and heading == pytest.approx(math.radians(-GAP_BEARING))


def test_pass_step_flies_through_the_measured_gap_and_the_check_gets_the_facts():
    from tests.test_live_qwen_handles import scheduler
    from uavlab.contracts import s_to_ns
    from uavlab.live_qwen.executive import check_request_text
    from uavlab.live_qwen.scheduler import GoalScheduler

    state = scheduler()
    assert isinstance(state, GoalScheduler)
    state.settings["architecture"]["perception"] = "openings"
    state.steps = [dict(kind="pass", objective="pass left opening", target="left opening")]
    state.plan, state.goal = dict(state.steps[0]), None
    scan = wall_scan()
    state.update(scan, s_to_ns(101), s_to_ns(101), False)
    assert state.goal is not None and state.goal.position.y > 0 and state.goal.position.x > WALL_X
    state.plan = dict(kind="condition", question="Is the left opening clear?")
    assert '"measured_openings"' in check_request_text(state, wall_scan(left_blocked=True))


@pytest.mark.parametrize("blocked,answer", [(False, "yes"), (True, "no")])
def test_a_sensor_answerable_check_is_routed_to_the_range_sensor(blocked, answer):
    from uavlab.live_qwen.openings import sensor_answer

    result = sensor_answer("Is the left opening clear?", wall_scan(left_blocked=blocked))
    assert result["answer"] == answer
    assert sensor_answer("Is the car red?", wall_scan()) is None


def test_follow_looks_again_while_moving_only_with_tracking():
    from tests.test_live_qwen_handles import scheduler
    from uavlab.contracts import Vec3, s_to_ns
    from uavlab.live_qwen.goals import Goal

    for mode, role in (("moving", "direction"), ("stop", None)):
        state = scheduler()
        state.settings["architecture"]["tracking"] = mode
        state.steps = [dict(kind="follow", objective="follow car", target="car", min_m=4,
                            max_m=6, duration_s=20)]
        state.plan = dict(state.steps[0])
        state.goal = Goal(3, Vec3(x=5, y=0, z=3), 0, False, s_to_ns(200), 1)
        moving = observation(speed=1.0)
        state.buffer.queue.append(dict(packet=1))
        assert state.next_role(moving, True) == role


def test_tracking_asks_for_moves_before_looking_again():
    from tests.test_live_qwen_handles import scheduler
    from uavlab.contracts import Vec3, s_to_ns
    from uavlab.live_qwen.goals import Goal

    state = scheduler()
    state.settings["architecture"]["tracking"] = "moving"
    state.steps = [dict(kind="follow", objective="follow car", target="car", min_m=4,
                        max_m=6, duration_s=20)]
    state.plan = dict(state.steps[0])
    state.goal = Goal(3, Vec3(x=5, y=0, z=3), 0, False, s_to_ns(200), 1)
    assert state.next_role(observation(), False) == "pilot"  # idle with a goal: move first


def test_a_hidden_target_behind_a_wall_flies_past_the_open_wall_end():
    from tests.test_live_qwen_handles import scheduler
    from uavlab.contracts import s_to_ns
    from uavlab.live_qwen.executive import detour

    state = scheduler()
    state.settings["architecture"]["perception"] = "openings"
    state.steps = [dict(kind="visit", objective="visit pillar", target="pillar", final=True)]
    state.plan, state.goal, state.detours = dict(state.steps[0]), None, 0
    assert detour(state, wall_scan(left_blocked=True), s_to_ns(101))
    assert state.goal is not None and state.detours == 1
