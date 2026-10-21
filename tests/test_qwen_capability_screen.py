"""Independent task gates for the local nine-task screen."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/diagnostics"))

from run_qwen_capability_suite import SCENARIOS, task_binding, task_pass

from uavlab.contracts.env_status import EnvironmentStatus

TASK_COUNT = 9
EPISODE_SECONDS = 60


@pytest.mark.parametrize("complete,stopped,collided,expected", [
    (True, True, False, True), (True, False, False, False),
    (False, True, False, False), (True, True, True, False),
])
def test_stop_does_not_override_task_or_safety(complete, stopped, collided, expected):
    _, mission, _ = task_binding("visible_target", {})
    status = EnvironmentStatus(t_sim_ns=0, position=dict(x=0, y=0, z=3),
                               distance_to_goal_m=1, task_complete=complete, collided=collided)
    assert task_pass(status, mission, stopped) is expected


def test_following_requires_window_success_not_nearness_or_stop():
    _, mission, _ = task_binding("follow_target", {})
    status = EnvironmentStatus(t_sim_ns=20_000_000_000, position=dict(x=0, y=0, z=3),
                               distance_to_goal_m=5, task_complete=True)
    assert task_pass(status, mission, False)
    assert not task_pass(status.model_copy(update=dict(task_complete=False)), mission, True)


def test_all_nine_existing_configs_keep_their_limits():
    assert len(SCENARIOS) == TASK_COUNT
    for name in SCENARIOS:
        config, mission, bound = task_binding(name, {})
        assert mission.instruction == config.instruction
        assert bound["flight_seconds"] == config.max_episode_s == EPISODE_SECONDS
        assert all(getattr(mission.success, key) == value
                   for key, value in config.params["success"].items())


def test_every_paper_architecture_resolves_from_one_base():
    import json

    from run_qwen_capability_suite import PAPER_MATRIX, load_settings

    names = json.loads(PAPER_MATRIX.read_text())["architectures"]
    for name in names:
        settings = load_settings(None, name)
        assert settings["paper_architecture"] == name
        assert settings["model_id"] == "qwen3-vl-4b-d207-shared"
        assert settings["pilot_mode"] in {"classical", "vla"}


def test_only_the_oracle_receives_the_evaluator_goal():
    from run_qwen_capability_suite import privileged_goal

    class Env:
        def debug_scene(self):
            return dict(goal=[6.0, 0.0, 1.0])

    bound = dict(goal_mode="visual")
    privileged_goal(bound, Env())
    assert bound == dict(goal_mode="numeric", oracle_goal=[6.0, 0.0, 1.0], oracle_visual=True)
