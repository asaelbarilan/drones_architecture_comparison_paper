import json
import math

import pytest

from uavlab.live_qwen.classical_pilot import classical_chunk, classical_payload
from uavlab.plugins.inference.action_buffer import ActionBuffer
from uavlab.plugins.reasoning.shared_qwen_pilot import pilot_action

STEP_S, SPEED, YAW_RATE = 0.1, 2.0, 1.0
CHUNK = 8
CLOSE_ENOUGH_M = 0.15


def test_far_goal_flies_at_speed_limit_along_goal_direction():
    steps = classical_chunk([10.0, 0.0, 0.0, 0.0], 8, STEP_S, SPEED, YAW_RATE)
    assert all(s[0] == pytest.approx(SPEED * STEP_S) for s in steps)
    assert all(s[1] == s[2] == s[3] == 0 for s in steps)


def test_near_goal_decelerates_and_never_overshoots():
    steps = classical_chunk([0.3, -0.1, 0.05, 0.0], 8, STEP_S, SPEED, YAW_RATE)
    travelled = [sum(s[i] for s in steps) for i in range(3)]
    assert math.dist(travelled, [0.3, -0.1, 0.05]) < CLOSE_ENOUGH_M
    assert all(abs(t) <= abs(g) + 1e-9 for t, g in zip(travelled, [0.3, -0.1, 0.05]))
    lengths = [math.dist(s[:3], [0, 0, 0]) for s in steps]
    assert lengths == sorted(lengths, reverse=True)


def test_yaw_is_clockwise_radians_and_rate_limited():
    steps = classical_chunk([0.0, 0.0, 0.0, 90.0], 8, STEP_S, SPEED, YAW_RATE)
    assert all(0 < s[3] <= YAW_RATE * STEP_S for s in steps)
    small = classical_chunk([0.0, 0.0, 0.0, -1.0], 8, STEP_S, SPEED, YAW_RATE)
    assert sum(s[3] for s in small) == pytest.approx(math.radians(-1.0))


@pytest.mark.parametrize("remaining", [[10, 2, 1.5, 11.1], [0.4, 0, 0, 0], [3, -3, -1, -170]])
def test_actions_execute_without_duration_stretch(remaining):
    for step in classical_chunk(remaining, 8, STEP_S, SPEED, YAW_RATE):
        assert pilot_action(step, 0.3, STEP_S, SPEED, YAW_RATE).duration_s == pytest.approx(STEP_S)


def test_payload_actions_fit_the_live_action_buffer():
    prompt = json.dumps(dict(instruction="Fly to the red pillar.", box=None,
                             state=[0, 0, 0, 0], remaining=[5.0, 0.5, 0.2, 3.0]))
    payload = classical_payload(prompt, 8, STEP_S, SPEED, YAW_RATE)
    buffer = ActionBuffer()
    buffer.begin(7, 3)
    for index, step in enumerate(payload["steps_fru_m_yaw_rad"]):
        buffer.append(dict(request_id=7, goal_version=3, index=index, tokens=[-1] * 4,
                           step_fru_m_yaw_rad=step, observed_ns=1, ready_ns=2, expires_ns=10))
    assert len(buffer.queue) == CHUNK
    assert payload["controller"] == "classical"


def test_rejects_malformed_goal_error():
    with pytest.raises(ValueError):
        classical_chunk([1.0, float("nan"), 0.0, 0.0], 8, STEP_S, SPEED, YAW_RATE)
