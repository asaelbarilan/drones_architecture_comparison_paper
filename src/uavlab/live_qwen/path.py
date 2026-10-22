"""D-165: shared SUPER local path planning for every waypoint architecture in the live runtime.

The harness's C0 ceiling flew through SUPER (collision-aware A* over the range fan with a
known-free commitment), but the live runtime handed the pilot the straight-line error to the
goal, so the shield halted every architecture in front of the first obstacle (D-164 seed 1060).
Here the authorized goal is planned with the same SUPER parameters as the harness C0 and the
pilot receives the error to a lookahead point ("carrot") on that path instead. The goal, its
yaw and its arrival test are unchanged. Native direct-VLA entries (C7/C8) do not use it.
"""

import math

from uavlab.contracts import WaypointGoal
from uavlab.plugins.planning.super import SuperLocalPlanner
from uavlab.plugins.reasoning.shared_qwen_pilot import remaining_fru

from .control import context

# Same parameters as configs/architectures/c0_oracle.yaml (the harness ceiling).
SUPER_PARAMS = dict(resolution_m=0.5, planning_horizon_m=16.0, commit_horizon_m=2.5,
                    sensing_horizon_m=25.0, temporal_window_s=12.0, clearance_margin_m=1.2)
REPLAN_NS = 500_000_000
LOOKAHEAD_M = 1.5


class PathFollower:
    def __init__(self, mission):
        self.mission = mission
        self.planner = SuperLocalPlanner(**SUPER_PARAMS)
        self.planner.reset(mission, 0)
        self.points, self.goal_version, self.planned_ns = (), None, None
        self.last_reason = "not planned"

    def replan(self, goal, obs, now):
        new_goal = goal.version != self.goal_version
        due = self.planned_ns is None or obs.t_sim_ns - self.planned_ns >= REPLAN_NS
        if not (new_goal or due):
            return
        request = WaypointGoal(target=goal.position, stop_at_target=goal.terminal)
        trajectory = self.planner.plan(request, context(self.mission, obs, now))
        self.last_reason = trajectory.reason or "planned"
        if trajectory.feasible and trajectory.points:
            self.points = tuple(point.position for point in trajectory.points)
        elif new_goal:
            self.points = ()  # an unplanned new goal is never flown blind
        self.goal_version, self.planned_ns = goal.version, obs.t_sim_ns

    def carrot(self, goal, obs):
        if obs.position.distance_to(goal.position) <= LOOKAHEAD_M:
            return goal.position
        for point in self.points:
            if obs.position.distance_to(point) >= LOOKAHEAD_M:
                return point
        return self.points[-1] if self.points else None

    def to_go(self, goal, obs):
        """Length still to fly along the current plan of this goal (plus the straight rest
        beyond its horizon); the straight distance when there is no plan for it."""
        straight = obs.position.distance_to(goal.position)
        if goal.version != self.goal_version or not self.points:
            return straight
        start = min(range(len(self.points)),
                    key=lambda i: obs.position.distance_to(self.points[i]))
        total, here = 0.0, obs.position
        for point in self.points[start:]:
            total, here = total + here.distance_to(point), point
        return total + here.distance_to(goal.position)

    def remaining(self, goal, obs, now):
        """The pilot's error to the path carrot; all zeros (hold) when no safe path exists."""
        self.replan(goal, obs, now)
        carrot = self.carrot(goal, obs)
        if carrot is None:
            return [0.0, 0.0, 0.0, 0.0]
        error = remaining_fru(carrot, obs.position, obs.yaw_rad, goal.yaw)
        return [float(v) if math.isfinite(v) else 0.0 for v in error]
