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
    assert '"search"' in oracle_program(state)
    state.planner_event = "target_lost"
    assert oracle_program(state) is None
    flat = SimpleNamespace(settings=dict(settings, architecture=dict(oracle_plan=True)),
                           planner_event=None)
    assert oracle_program(flat) is None
