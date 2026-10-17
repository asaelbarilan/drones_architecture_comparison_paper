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
