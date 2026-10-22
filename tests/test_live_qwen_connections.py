"""D-182 connection handles for architectures without a planner: H3, H4, H9 (CPU only)."""

import json
from pathlib import Path

import numpy as np
import pytest

from tests.test_live_qwen import ORIGIN_NS, ManualWorker, observation
from uavlab.contracts import CameraIntrinsics, SensorRef, s_to_ns
from uavlab.core.frame_store import global_store
from uavlab.live_qwen.architecture import accept_native_line, unplanned_steps
from uavlab.live_qwen.runner import mission_spec
from uavlab.live_qwen.scheduler import GoalScheduler

FIND = ("Find the red pillar, which may be outside the current view. "
        "Fly to it and stop within 2 metres.")
HOVER = ("Approach the red pillar and hover about 1 metre before it on your approach side. "
         "Hold for 2 continuous seconds, then finish.")
PILLAR_M = 12.0


def unplanned(mission, **switches):
    settings = json.loads(Path("configs/experiments/qwen_async_local.json").read_text())
    base = dict(goal_source="instruction", monitor="none", recovery="none", memory=False)
    settings["architecture"] = dict(base, **switches)
    settings["goal_mode"] = "visual"
    case = dict(settings["missions"][0], instruction=mission)
    state = GoalScheduler(ManualWorker(), mission_spec(case, settings), settings, lambda row: None)
    state.update(observation(), ORIGIN_NS, ORIGIN_NS, False)
    return state


def ranged(depth_m):
    obs = observation().model_copy(update=dict(
        intrinsics=CameraIntrinsics(width=16, height=16, fx=8, fy=8, cx=8, cy=8),
        depth=SensorRef(kind="depth", uri="connections-depth", digest="test")))
    global_store().put("connections-depth", np.full((16, 16), depth_m))
    return obs


@pytest.mark.parametrize("search,started", [("planner", False), ("policy", True)])
def test_h3_a_find_mission_searches_without_a_planner_only_with_the_policy(search, started):
    state = unplanned(FIND, search=search)
    state.target_absent(observation(), ORIGIN_NS, ORIGIN_NS + s_to_ns(1))
    assert (state.search_goal is not None) is started


@pytest.mark.parametrize("completion,stated", [("default", {}),
                                               ("evidence", dict(standoff_m=1.0, hold_s=2.0))])
def test_h4_reads_the_stated_standoff_and_hold_of_an_unplanned_mission(completion, stated):
    state = unplanned(HOVER, completion=completion)
    step = unplanned_steps(state)[0]
    assert {k: step[k] for k in ("standoff_m", "hold_s") if k in step} == stated


def native(measure, completion="default"):
    state = unplanned("Fly to the red pillar and stop within 2 metres.", goal_source="vla_native",
                      measure=measure, completion=completion)
    state.settings["goal_mode"] = "numeric"
    state.pending_depth = None
    return state


def test_h9_the_vla_box_gets_the_measured_distance_and_a_far_object_is_not_terminal():
    line = dict(box=[440, 286, 520, 500], left=[2.6, 0.0, 0.0, 0.0])
    written = native("model")
    accept_native_line(written, line, ranged(PILLAR_M), ORIGIN_NS)
    assert written.goal.position.x == pytest.approx(2.6) and written.goal.terminal
    measured = native("range")
    accept_native_line(measured, line, ranged(PILLAR_M), ORIGIN_NS)
    goal = measured.goal
    assert goal.position.x == pytest.approx(10.0, abs=0.5) and not goal.terminal  # one 10 m leg
    near = native("range")
    accept_native_line(near, line, ranged(5.0), ORIGIN_NS)
    assert near.goal.terminal  # the object is within one leg: arrival may finish


def test_h4_a_measured_leg_that_ends_short_looks_again_instead_of_finishing():
    from uavlab.live_qwen.connections import look_again

    state = native("range", completion="evidence")
    accept_native_line(state, dict(box=[440, 286, 520, 500], left=[2.6, 0, 0, 0]),
                       ranged(PILLAR_M), ORIGIN_NS)
    assert look_again(state, ORIGIN_NS + s_to_ns(1)) and state.goal is None
    assert not state.stopped


def test_h9_needs_only_the_box_when_the_written_line_is_cut_off():
    state = native("range")
    accept_native_line(state, dict(box=[375, 0, 775, 756], left=None), ranged(2.4), ORIGIN_NS)
    assert state.goal is not None and state.goal.terminal
    with pytest.raises(ValueError):
        accept_native_line(native("model"), dict(box=[375, 0, 775, 756], left=None),
                           ranged(2.4), ORIGIN_NS)
