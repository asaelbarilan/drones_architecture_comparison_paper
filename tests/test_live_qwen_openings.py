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
