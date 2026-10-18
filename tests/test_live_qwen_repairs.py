import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.test_live_qwen import ORIGIN_NS, observation
from tests.test_live_qwen import state as scheduler_fixture
from uavlab.contracts import ControlCommand, Vec3, s_to_ns
from uavlab.live_qwen.goals import interpret_goal
from uavlab.live_qwen.mission_plan import accept_plan, validate_direction
from uavlab.live_qwen.search import MAX_TURNS, search_command, start_search, update_search
from uavlab.live_qwen.world_contract import normalize_world

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/diagnostics"))
from probe_qwen_decoder_graph import MAX_GRAPHS, DecoderGraph

state = scheduler_fixture
WORLD_TEXT = "Fly to world ENU coordinate (12, 0, 3) metres and stop within 2 metres."
FRESHNESS_SECONDS = 1.5


def test_explicit_world_is_absolute_not_added_to_start_altitude(state):
    state, _ = state
    state.mission = state.mission.model_copy(update=dict(instruction=WORLD_TEXT))
    accept_plan(state, dict(steps=[dict(objective=WORLD_TEXT, target=[12, 0, 3])]), ORIGIN_NS)
    data = validate_direction(state, dict(kind="world", target={"world_enu": [12, 0, 3]}))
    position, yaw, terminal = interpret_goal(data, observation(), state.origin, state.settings)
    assert position == Vec3(x=12, y=0, z=3)
    assert yaw == state.origin.yaw_rad
    assert terminal
    alias = validate_direction(state, dict(kind="world", target=[12, 0, 3]))
    assert alias == data
    with pytest.raises(ValueError, match="changed committed"):
        validate_direction(state, dict(kind="world", target=[12, 0, 6]))


def test_invented_world_coordinate_rejected():
    payload = dict(steps=[dict(objective="go", target={"world_enu": [10, 0, 3]})])
    with pytest.raises(ValueError, match="exactly match"):
        normalize_world(payload, WORLD_TEXT)
    with pytest.raises(ValueError, match="exactly match"):
        normalize_world(payload, "Find the red pillar")


def test_relative_pose_schema_is_not_silently_padded():
    payload = dict(steps=[dict(objective="go", target=[1, 0, 0])])
    assert normalize_world(payload, "Fly forward") == payload


def test_search_turn_is_bounded_rotation_not_translation_or_completion(state):
    state, _ = state
    state.mission = state.mission.model_copy(update=dict(instruction="Find the red pillar"))
    state.target_missing = True
    start_search(state, ORIGIN_NS)
    command = search_command(state, observation(), ControlCommand(
        t_sim_ns=0, velocity=Vec3(x=0, y=0, z=0), yaw_rate_rps=0))
    assert command.velocity.norm() == 0
    assert abs(command.yaw_rate_rps) <= state.settings["max_yaw_rate_rps"]
    assert command.expires_t_sim_ns == s_to_ns(.2)
    assert update_search(state, observation(yaw=-math.pi/4), ORIGIN_NS+s_to_ns(1))
    assert state.search_goal is None and not state.stopped
    assert not state.target_missing


def test_search_requires_mission_permission_and_stops_after_full_sweep(state):
    state, _ = state
    state.target_missing = True
    with pytest.raises(ValueError, match="explicit search"):
        start_search(state, ORIGIN_NS)
    state.mission = state.mission.model_copy(update=dict(instruction="Find the red pillar"))
    state.search_turns = MAX_TURNS
    with pytest.raises(ValueError):
        start_search(state, ORIGIN_NS)


def test_shape_cache_evicts_lru_after_gpu_sync_without_growing():
    syncs = []
    cuda = SimpleNamespace(synchronize=lambda: syncs.append(True))
    graph = DecoderGraph(SimpleNamespace(forward=lambda: None),
                         SimpleNamespace(cuda=cuda))
    graph.capture = lambda value: value
    for index in range(MAX_GRAPHS):
        assert graph.cached(index, str(index)) == str(index)
    assert graph.cached(0, "ignored") == "0"
    graph.latest = "old output pointer"
    assert graph.cached(MAX_GRAPHS, "new") == "new"
    assert len(graph.entries) == MAX_GRAPHS and 0 in graph.entries and 1 not in graph.entries
    assert syncs == [True] and graph.latest is None


def test_repair_action_horizon_fits_original_freshness_budget():
    settings = json.loads(Path("configs/experiments/qwen_capability_repair.json").read_text())
    assert settings["action_duration_s"] * settings["stream_actions"] < settings["pilot_ttl_s"]
    assert settings["pilot_ttl_s"] == FRESHNESS_SECONDS
