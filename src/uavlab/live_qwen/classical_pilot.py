"""Classical waypoint controller with the VLA pilot's exact input/output contract.

Baseline for the VLA-vs-classical comparison: it reads only the pilot prompt's
body-frame goal error (forward, right, up metres; clockwise degrees) and returns
the same eight body-frame steps (forward, right, up metres; clockwise radians).
No image, no learned weights. Speed follows a constant-deceleration profile so
it stops at the goal instead of overshooting.
"""

import json
import math

DECEL_MPS2 = 1.0
YAW_RATE_FRACTION = 0.8  # stay under the yaw-rate limit so actions are never stretched
GOAL_CHANNELS = 4


def classical_chunk(remaining, count, step_s, max_speed_mps, max_yaw_rate_rps):
    if len(remaining) != GOAL_CHANNELS or any(not math.isfinite(v) for v in remaining):
        raise ValueError("classical pilot needs a finite four-channel goal error")
    offset = [float(v) for v in remaining[:3]]
    yaw = math.radians(remaining[3])
    yaw_step_max = max_yaw_rate_rps * YAW_RATE_FRACTION * step_s
    steps = []
    for _ in range(count):
        distance = math.sqrt(sum(v * v for v in offset))
        speed = min(max_speed_mps, math.sqrt(2 * DECEL_MPS2 * distance))
        length = min(distance, speed * step_s)
        move = [v / distance * length for v in offset] if distance > 0 else [0.0, 0.0, 0.0]
        turn = max(-yaw_step_max, min(yaw_step_max, yaw))
        steps.append([*move, turn])
        offset = [v - m for v, m in zip(offset, move, strict=False)]
        yaw -= turn
    return steps


def classical_payload(prompt, count, step_s, max_speed_mps, max_yaw_rate_rps):
    data = json.loads(prompt)
    steps = classical_chunk(data["remaining"], count, step_s, max_speed_mps, max_yaw_rate_rps)
    return dict(steps_fru_m_yaw_rad=steps, tokens=[], remaining_supplied=data["remaining"],
                controller="classical")
