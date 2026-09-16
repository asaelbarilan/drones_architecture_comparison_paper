"""Diagnostic stop must not censor a moving detour or an active scan."""

from copy import deepcopy

from scripts.run_commitment_pair import configs, repetition


def sample():
    controls = [dict(t=t, position=[0, 0, 3], yaw_rate=0) for t in range(46)]
    goals = [dict(t=t, kind="exploration", goal=[2, 2, 3]) for t in range(0, 46, 2)]
    return controls, goals


def test_stationary_repeated_failure():
    controls, goals = sample()
    assert repetition(controls, goals, 45)


def test_ongoing_detour_is_not_censored():
    controls, goals = sample()
    for c in controls:
        c["position"][0] = c["t"] * 0.1
    assert not repetition(controls, goals, 45)


def test_scan_and_changed_goals_are_not_censored():
    controls, goals = sample()
    rotated = deepcopy(controls)
    rotated[-1]["yaw_rate"] = 0.4
    assert not repetition(rotated, goals, 45)
    goals[-1]["goal"] = [5, 2, 3]
    assert not repetition(controls, goals, 45)


def test_short_pause_is_not_censored():
    controls, goals = sample()
    assert not repetition(controls[:31], goals[:15], 30)


def test_pair_configs_only_change_commitment():
    arches, env = configs()
    assert env.max_episode_s == 240
    assert arches["off"].policy.params["target_commitment_s"] == 0
    assert arches["on"].policy.params["target_commitment_s"] == 20
