"""Connection handles for the architectures without a planner (D-182).

H1/H2/H5 act on the planner -> executor connection, which only FULL, C10 and C13 have. These
handles act on connections C2-C8 already have; no box is added to any architecture:
- H3 search policy: target absent -> the bounded camera search, when the mission asks to find.
  Without a planner nothing authorizes that search, so C2-C5 never look around (C6's recovery
  planner and FULL's planner do).
- H4 evidence-based completion: the stated standoff / hold are read from the mission text (the
  planned path reads them from each step), and the last fresh grounding of the object counts as
  object-below arrival even without a memory box. A measured leg that ends short of the object
  looks again instead of finishing.
- H9 measured distance: the VLA's own box gives the bearing and the depth sensor the distance,
  instead of the distance the VLA writes ("+2.6 m" for a 12 m pillar, D-163). The sensor
  answers what it can measure, as in H5.
Inputs are the mission text, the camera, the depth image and onboard state; never evaluator
truth.
"""

from .architecture import switch
from .goals import visual_goal
from .grounding import observed_range
from .mission_plan import add_stated_fields
from .stop_rules import aim_standoff

MIN_LEG_M = 0.5


def search_policy(state):
    """H3: the bounded search may start without a planner's authorization."""
    return switch(state.settings, "search") == "policy"


def evidence(state):
    return switch(state.settings, "completion") == "evidence"


def stated_steps(state, steps):
    """H4: stated standoff / hold from the mission text, as parse_steps does for plans."""
    if evidence(state):
        for step in steps:
            add_stated_fields(step)
    return steps


def keeps_grounding(state):
    """The last fresh grounding is kept for object-below arrival (memory box or H4)."""
    return switch(state.settings, "memory") or evidence(state)


def measured_line(state, data, source):
    """H9: (position, yaw, terminal) toward the VLA's own box at the measured range, else None.

    terminal is False when the object is farther than one bounded leg, so H4 looks again."""
    box = data.get("box")
    if switch(state.settings, "measure") != "range" or not isinstance(box, list):
        return None
    u, v = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    distance = observed_range(dict(target=dict(u=u, v=v)), source, state.pending_depth)
    if distance is None:
        return None
    limit = state.settings["max_goal_m"]
    travel = distance - aim_standoff(state)
    leg = dict(u=u, v=v, travel_m=min(limit, max(MIN_LEG_M, travel)), target_visible=True,
               box=box)
    position, yaw = visual_goal(leg, source, state.settings)
    return position, yaw, travel <= limit


def look_again(state, now):
    """H4: a measured leg that ended short of the object asks for a fresh line / look."""
    # Only a measured H9 leg (D-187): other non-terminal goals, such as the C1 skill agent's
    # goto, finish through their own owner and must not be turned into a new look.
    if (state.goal is None or state.goal.terminal or not evidence(state)
            or switch(state.settings, "measure") != "range"):
        return False
    state.replan("measured leg reached; look again", now)
    return True
