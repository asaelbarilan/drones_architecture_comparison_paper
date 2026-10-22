"""Planner-authorized, bounded in-place camera search; never claims task completion."""

import math
import re

from uavlab.contracts import s_to_ns

from .goals import angle_error

TURN = math.pi / 4
MAX_TURNS = 8
TURN_TIMEOUT_S = 4
ARRIVAL_DEGREES = 3


def search_allowed(state):
    requested = bool(re.search(r"\b(find|search)\b", state.mission.instruction, re.I))
    # H2 (D-170): typed steps the executive authorizes to look for an out-of-view object.
    requested |= (state.plan or {}).get("kind") in ("search", "visit", "pass", "follow")
    return state.target_missing and requested and state.search_turns < MAX_TURNS


def start_search(state, now):
    if not search_allowed(state) or state.last_yaw is None:
        raise ValueError("search turn requires an absent target and explicit search mission")
    state.pause("planner authorized in-place search", now)
    state.search_turns += 1
    state.search_goal = state.last_yaw - TURN
    state.search_deadline = now+s_to_ns(TURN_TIMEOUT_S)
    state.log("search_started", now, yaw=state.search_goal, turn=state.search_turns)


def update_search(state, obs, now):
    if state.search_goal is None:
        return False
    arrived = abs(math.degrees(angle_error(state.search_goal, obs.yaw_rad))) <= ARRIVAL_DEGREES
    if arrived or now >= state.search_deadline:
        state.search_goal = None
        state.target_missing = False
        state.replan("search view reached" if arrived else "search turn timed out", now)
        state.log("search_finished", now, arrived=arrived)
    return True


def search_command(state, obs, command):
    error = angle_error(state.search_goal, obs.yaw_rad)
    limit = state.settings["max_yaw_rate_rps"]
    rate = min(limit, max(-limit, error*2))
    return command.model_copy(update=dict(yaw_rate_rps=rate,
                                          expires_t_sim_ns=obs.t_sim_ns+s_to_ns(.2),
                                          source_decision_id="bounded_search_turn"))
