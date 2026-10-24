"""D-185 privileged oracle swaps: the true box only for visible objects; the plan oracle (CPU)."""

import math
from types import SimpleNamespace

import numpy as np
import pytest

from tests.test_live_qwen import observation
from uavlab.contracts import CameraIntrinsics
from uavlab.live_qwen.oracles import PILLAR, camera_point, named_object, true_box
from uavlab.plugins.reasoning.spf import SPFPoint, point_to_enu

INTR = CameraIntrinsics(width=224, height=224, fx=112, fy=112, cx=112, cy=112)
SETTINGS = dict(camera_pitch_rad=-0.1)
FAR = 40.0
CENTRE = 500


def seen(yaw=0.0):
    return observation(yaw=yaw).model_copy(update=dict(intrinsics=INTR))


def test_the_projection_inverts_point_to_enu():
    obs = seen(yaw=0.3)
    world = point_to_enu(SPFPoint(620, 410, 1), position=obs.position, yaw_rad=obs.yaw_rad,
                         width=224, height=224, fx=112, fy=112, cx=112, cy=112,
                         camera_pitch_rad=-0.1, distance_m=7.0, min_altitude_m=0.0)
    forward, right, up = camera_point((world.x, world.y, world.z), obs, -0.1)
    assert forward == pytest.approx(7.0)
    assert 112 + right * 112 / forward == pytest.approx(620 * 224 / 1000)
    assert 112 - up * 112 / forward == pytest.approx(410 * 224 / 1000)


def test_a_visible_pillar_gets_a_box_around_it_and_a_hidden_one_gets_none():
    pillar = ("red pillar", np.array([10.0, 0.0, 3.0]), PILLAR)
    open_view = np.full((224, 224), FAR)
    box = true_box(pillar, seen(), SETTINGS, open_view)
    assert box is not None and box[0] < CENTRE < box[2]  # straight ahead, centred
    wall = np.full((224, 224), 4.0)  # a wall 4 m ahead hides the pillar at 10 m
    assert true_box(pillar, seen(), SETTINGS, wall) is None
    assert true_box(pillar, seen(yaw=math.pi), SETTINGS, open_view) is None  # behind


def test_the_step_names_its_object_by_colour_or_vehicle_orientation():
    objects = [("red pillar", None, PILLAR), ("blue pillar", None, PILLAR),
               ("overturned vehicle", None, PILLAR), ("upright vehicle", None, PILLAR)]
    assert named_object(objects, "blue pillar")[0] == "blue pillar"
    assert named_object(objects, "Visit the red pillar first, then the blue")[0] == "red pillar"
    assert named_object(objects, "the upside-down car")[0] == "overturned vehicle"
    assert named_object(objects, "left opening") is None


def test_the_plan_oracle_feeds_the_typed_contract_once_and_never_recovery():
    from uavlab.live_qwen.oracles import oracle_program

    settings = dict(architecture=dict(contract="typed", oracle_plan=True),
                    oracle_program=[dict(kind="search", object="red pillar")])
    state = SimpleNamespace(settings=settings, planner_event=None)
    from uavlab.live_qwen.contract import parse_contract

    program, repairs = parse_contract(oracle_program(state), "Find the red pillar.")
    assert program[0]["kind"] == "search" and repairs == []  # the same parser as the model
    state.planner_event = "target_lost"
    assert oracle_program(state) is None
    flat = SimpleNamespace(settings=dict(settings, architecture=dict(oracle_plan=True)),
                           planner_event=None)
    assert oracle_program(flat) is None


def test_a_pillar_whose_centre_is_behind_a_low_wall_shows_its_top():
    """D-185 fix: the visible part above a low wall counts; a fully hidden pillar still not."""
    pillar = ("red pillar", np.array([12.0, 0.0, 3.0]), PILLAR)
    obs = seen()
    depth = np.full((224, 224), FAR)
    depth[100:, :] = 6.0  # a low wall 6 m ahead covers everything from row 100 down
    box = true_box(pillar, obs, SETTINGS, depth)
    assert box is not None and box[3] <= 100 * 1000 / 224 + 8  # only the part above the wall
    assert true_box(pillar, obs, SETTINGS, np.full((224, 224), 6.0)) is None


def test_a_delayed_oracle_look_is_applied_only_after_the_matched_latency():
    from uavlab.live_qwen.oracles import release_look

    applied = []
    state = SimpleNamespace(oracle_pending=(5, dict(target_visible=False, box=None), seen(), 1,
                                            None),
                            pending_depth=None, log=lambda *a, **k: None,
                            accept_goal=lambda payload, *a: applied.append(payload))
    release_look(state, 4)
    assert applied == [] and state.oracle_pending is not None
    release_look(state, 5)
    assert len(applied) == 1 and state.oracle_pending is None
