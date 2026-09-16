"""An altitude violation must not be diagnosed as a horizontal geofence crossing."""

from types import SimpleNamespace

import pytest

from uavlab.contracts import TerminationReason, Vec3
from uavlab.contracts.env_status import EnvironmentStatus
from uavlab.core.compose import load_architecture, load_environment
from uavlab.core.config import EpisodeSpec
from uavlab.core.orchestrator import Orchestrator


@pytest.mark.parametrize(
    "altitude,expected",
    [
        (0.499768024158146, "below minimum altitude"),
        (7.01, "above maximum altitude"),
        (3.0, "left permitted flight bounds; altitude is within mission limits"),
    ],
)
def test_bounds_diagnostic_identifies_altitude_without_changing_termination(altitude, expected):
    runner = Orchestrator(
        load_architecture("c0"),
        load_environment("capability_visible_target_slow_240_dev"),
        EpisodeSpec(episode_id="bounds-diagnostic", seed=1061),
    )
    runner._build_components()
    status = EnvironmentStatus(
        t_sim_ns=0,
        position=Vec3(x=44.4620970262886, y=0, z=altitude),
        distance_to_goal_m=32.558,
        out_of_bounds=True,
    )
    runner.env = SimpleNamespace(status=lambda: status)
    assert runner._check_termination()
    assert runner._termination is TerminationReason.OUT_OF_BOUNDS
    assert runner._termination_detail.startswith(expected)
