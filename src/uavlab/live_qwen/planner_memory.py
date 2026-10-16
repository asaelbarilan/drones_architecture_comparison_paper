"""Bounded event memory and recovery authority; committed mission stays immutable."""

import json

from uavlab.contracts import s_to_ns

MEMORY_LIMIT = 16
MAX_REASON = 400
RECOVERY = '''You are the event-driven mission planner. Preserve the original mission,
ordered committed steps and completed steps. A local waypoint is not a subgoal.
Review the trigger and observation memory. Choose exactly one action:
retry_current (retry the same objective), refresh_view (request fresh visual
grounding for that same objective), hold (temporary stationary safety pause).
Do not invent motion, skip steps, change target identity or claim completion.
Return JSON with exactly action and reason. Reason at most 15 words.
Use refresh_view for a lost target or stale perception, retry_current for
recoverable stalled progress, hold for unsafe or unresolved conflicting evidence.
Context: '''


def remember(state, event, now, **details):
    entry = dict(event=event, wall_ns=now, step_index=state.step_index, **details)
    state.memory = [*state.memory, entry][-MEMORY_LIMIT:]
    state.log("planner_memory", now, entry=entry)


def planner_context(state):
    return dict(original_mission=state.mission.instruction,
                committed_steps=state.steps, active_step=state.step_index,
                completed_steps=state.completed, trigger=state.planner_event,
                observations=state.memory, feedback=state.feedback)


def accept_recovery(state, payload, now):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict) or set(data) != {"action", "reason"}:
        raise ValueError("planner recovery requires action and reason")
    if data["action"] not in {"retry_current", "refresh_view", "hold"}:
        raise ValueError("planner recovery cannot change mission or complete it")
    if not isinstance(data["reason"], str) or not 1 <= len(data["reason"]) <= MAX_REASON:
        raise ValueError("invalid planner recovery reason")
    remember(state, "planner_decision", now, trigger=state.planner_event, **data)
    state.planner_event = None
    state.replan("planner recovery: " + data["reason"], now)
    if data["action"] == "hold":
        state.hold_until = now+s_to_ns(state.settings["monitor_retry_s"])
