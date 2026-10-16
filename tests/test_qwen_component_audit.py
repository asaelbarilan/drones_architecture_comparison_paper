"""Independent ordering and hold checks must reject misleading final poses."""

import importlib
import math
from pathlib import Path

import pytest


@pytest.fixture
def audit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts/diagnostics"))
    return importlib.import_module("audit_qwen_components")


def tick(time, forward, heading):
    return dict(kind="tick", wall_ns=time, position=dict(x=forward, y=0, z=3),
                yaw=-math.radians(heading))


def criteria():
    return dict(endpoint_tolerance_m=.5, heading_tolerance_deg=5,
                hold_max_displacement_m=.1, hold_max_heading_drift_deg=1)


def test_correct_final_pose_does_not_hide_wrong_order(audit):
    rows = [tick(1, 0, 0), tick(2, 0, 15), tick(3, 1, 15)]
    rows.append(dict(kind="replan", reason="intermediate goal reached; advance mission"))
    result = audit.movement_checks(rows, dict(id="move_then_turn"), criteria())
    assert not result["sequence_pass"]


def test_sequence_needs_explicit_goal_advance(audit):
    rows = [tick(1, 0, 0), tick(2, 1, 0), tick(3, 1, 15)]
    assert not audit.movement_checks(rows, dict(id="move_then_turn"), criteria())["sequence_pass"]
    rows.append(dict(kind="replan", reason="intermediate goal reached; advance mission"))
    assert audit.movement_checks(rows, dict(id="move_then_turn"), criteria())["sequence_pass"]


def test_return_to_start_does_not_pass_hold(audit):
    rows = [tick(1, 0, 0), tick(2, .2, 0), tick(3, 0, 0)]
    assert not audit.movement_checks(rows, dict(id="hold"), criteria())["hold_pass"]


def test_stationary_hold_passes_without_executed_actions(audit):
    rows = [tick(1, 0, 0), tick(2, 0, 0)]
    assert audit.movement_checks(rows, dict(id="hold"), criteria())["hold_pass"]
    rows.append(dict(kind="action_consumed"))
    assert not audit.movement_checks(rows, dict(id="hold"), criteria())["hold_pass"]
