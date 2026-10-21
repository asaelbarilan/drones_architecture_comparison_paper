"""H2 (D-168): one owner executes the typed program's kinds.

The basic executor treats every step as "fly to the target, stop when the monitor agrees".
This executive is the single owner of sequencing for a typed contract (contract.py):
- condition: asks the shared VLM one yes/no question about the current image when the step
  becomes active, then splices the chosen branch into the program;
- pass: aims beyond the grounded opening and completes on arrival, never stopping at it;
- follow: keeps the object at its stated distance band and completes only after the stated
  duration (never stops early);
- visit: intermediate visits advance; a stated dwell becomes a hold; the final one stops;
- search: authorizes the bounded camera search for that step;
- goto: a numeric step.
Inputs are the planner's contract, the camera and onboard state; never evaluator truth.
"""

import json

from uavlab.contracts import s_to_ns

from .architecture import switch
from .contract import executable, flattened, is_numeric, parse_contract

CHECK = '''Answer the yes/no question about THIS camera image. Return ONLY JSON
{"answer":"yes" or "no","reason":"at most 15 words"}. Question: '''
PASS_BEYOND_M = 2.0
HOLD = "hold"
MAX_REASON = 200


def active(state):
    return switch(state.settings, "executive") == "kinds"


def typed(state):
    return switch(state.settings, "contract") == "typed"


def kind(state):
    return (state.plan or {}).get("kind") if active(state) else None


def accept_contract(state, payload, now):
    """H1: the typed program; executed by kind (H2) or flattened into plain steps."""
    program = parse_contract(payload, state.mission.instruction)
    steps = [executable(n) if active(state) else flattened(n) for n in program]
    if state.steps and steps != state.steps:
        raise ValueError("replanning cannot replace the committed program")
    state.steps = steps
    state.plan = dict(steps[state.step_index])
    state.log("mission_plan_committed", now, mission=state.mission.instruction,
              authored=payload, steps=steps, step_index=state.step_index, contract="typed")
    on_step(state, now)


def on_step(state, now):
    """A new program step became active: set its goal mode and kind-specific state."""
    if not active(state) or state.plan is None:
        return
    state.settings["goal_mode"] = "numeric" if is_numeric(state.plan) else "visual"
    state.follow_started = None
    if state.plan.get("kind") == "search":
        state.search_authorized = True
    state.log("step_activated", now, step_index=state.step_index, step_kind=state.plan.get("kind"))


def check_request_text(state):
    return CHECK + state.plan["question"]


def accept_check(state, payload, now):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict) or set(data) != {"answer", "reason"}:
        raise ValueError("condition check requires answer and reason")
    if data["answer"] not in ("yes", "no") or len(str(data["reason"])) > MAX_REASON:
        raise ValueError("condition answer must be yes or no")
    branch = state.plan["then" if data["answer"] == "yes" else "else"]
    index = state.step_index
    state.steps = [*state.steps[:index], *branch, *state.steps[index + 1:]]
    state.log("condition_answered", now, question=state.plan["question"], **data,
              branch_steps=branch)
    state.replan("condition answered " + data["answer"], now)
    on_step(state, now)


def adjust_visual(state, proposal, distance, now):
    """pass / follow change the visual leg; returns the proposal, HOLD, or None (default)."""
    step_kind = kind(state)
    target = proposal["target"]
    limit = state.settings["max_goal_m"]
    if step_kind == "pass":
        target["travel_m"] = min(limit, (distance or 1.0) + PASS_BEYOND_M)
        return proposal
    if step_kind != "follow":
        return None
    if state.follow_started is None:
        state.follow_started = now
        state.log("follow_started", now, duration_s=state.plan["duration_s"])
    middle = (state.plan["min_m"] + state.plan["max_m"]) / 2
    if distance is not None and distance <= middle:
        return HOLD  # inside the band's near half: watch, do not close in
    target["travel_m"] = min(limit, max(0.5, (distance or middle + 1.0) - middle))
    return proposal


def follow_done(state, now):
    return (kind(state) == "follow" and state.follow_started is not None
            and now - state.follow_started >= s_to_ns(state.plan["duration_s"]))


def pass_arrived(state, obs):
    return kind(state) == "pass" and state.goal is not None and state.goal.arrived(
        obs, state.settings)
