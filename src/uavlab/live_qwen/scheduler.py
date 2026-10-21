"""Event-driven role scheduler: persistent goals, one GPU owner, no control waits."""

import math

from uavlab.contracts import s_to_ns
from uavlab.plugins.inference.action_buffer import ActionBuffer, action_record
from uavlab.plugins.inference.qwen_worker import WorkItem
from uavlab.plugins.reasoning.shared_qwen_pilot import parse_monitor

from .architecture import (
    accept_native_line,
    commit_unplanned,
    no_monitor,
    recovery_due,
    switch,
    unverified_direction,
)
from .goals import Goal, angle_error, interpret_goal
from .grounding import capture_depth, grounded_direction, observed_range
from .mission_plan import accept_plan, validate_direction
from .planner_memory import accept_recovery, remember
from .prompts import role_request
from .search import search_allowed, start_search, update_search
from .skills import accept_skill, detected, skill_tick
from .skills import active as skills_active
from .skills import finished as skill_finished
from .stop_rules import (
    aim_standoff,
    hold_required_ns,
    near_limit,
    object_below,
    remember_object,
    start_hold,
)
from .visual_progress import fresh_evidence, record_grounding
from .world_contract import world_target

MIN_LEG_MARGIN_M = 0.1


class GoalScheduler:
    def __init__(self, worker, mission, settings, record):
        self.worker, self.mission, self.settings, self.record = worker, mission, settings, record
        self.buffer = ActionBuffer()
        self.plan = self.goal = self.origin = self.pending = None
        self.version, self.next_id, self.failures = 0, 0, 0
        self.monitor_reason = None
        self.feedback, self.completed = "initial mission", []
        self.yaw_total, self.last_yaw = 0.0, 0.0
        self.last_monitor = self.progress_at = 0
        self.best_distance = self.best_heading = math.inf
        self.stopped = self.failed = False
        self.motion_epoch = 0
        self.steps, self.step_index, self.hold_until = [], 0, 0
        self.visual_stop_pending = False
        self.pending_depth = None
        self.memory, self.planner_event = [], None
        self.visual_evidence = self.visual_source = None
        self.target_missing = False
        self.search_goal, self.search_deadline, self.search_turns = None, 0, 0
        self.search_authorized = False
        self.object_memory = self.hold_started = None
        self.last_obs, self.last_recovery = None, 0
        self.skill, self.skill_turns, self.skill_history, self.skill_until = None, 0, [], 0

    def log(self, kind, now, **data):
        self.record(dict(kind=kind, wall_ns=now, goal_version=self.version, **data))

    def pause(self, reason, now):
        self.buffer.revoke()
        self.motion_epoch += 1
        if self.worker.current is not None:
            self.worker.revoke()
        self.log("motion_revoked", now, reason=reason)

    def request_monitor(self, reason, now):
        if self.goal is None or self.monitor_reason is not None:
            return
        if switch(self.settings, "monitor") == "none":
            no_monitor(self, reason, now)
            return
        self.pause(reason, now)
        self.monitor_reason = reason

    def replan(self, reason, now):
        self.pause(reason, now)
        self.version += 1
        self.plan = self.goal = self.hold_started = None
        if self.steps:
            self.plan = dict(self.steps[self.step_index])
        self.monitor_reason = None
        self.feedback = reason
        self.log("replan", now, reason=reason)

    def update(self, obs, captured_ns, now, moving):
        self.last_obs = obs
        if self.origin is None:
            self.origin, self.last_yaw = obs, obs.yaw_rad
            self.progress_at = self.last_monitor = self.last_recovery = now
            if switch(self.settings, "goal_source") in ("instruction", "oracle", "vla_native"):
                commit_unplanned(self, now)
        self.yaw_total += angle_error(obs.yaw_rad, self.last_yaw)
        self.last_yaw = obs.yaw_rad
        for event in self.worker.poll(self.version, now):
            self.receive(event, obs, now)
        if self.hold_started is not None:
            self.check_hold(obs, now)
            return
        if skill_tick(self, now):
            return
        if update_search(self, obs, now):
            return
        self.check_events(obs, now)
        if now < self.hold_until:
            return
        if self.stopped or self.failed or self.worker.current is not None:
            return
        role = self.next_role(obs, moving)
        if role:
            self.submit(role, obs, captured_ns)

    def next_role(self, obs, moving):
        if self.planner_event:
            return "planner" if obs.velocity.norm() <= self.settings["stopped_mps"] else None
        if self.monitor_reason:
            return "monitor" if obs.velocity.norm() <= self.settings["stopped_mps"] else None
        if self.plan is None:
            return "planner"
        if self.goal is None:
            native = switch(self.settings, "goal_source") == "vla_native"
            role = "vla_line" if native else "direction"
            return role if obs.velocity.norm() <= self.settings["stopped_mps"] else None
        if not moving and not self.buffer.queue and not self.goal.arrived(obs, self.settings):
            return "pilot"
        return None

    def submit(self, role, obs, captured):
        ttl = self.settings["pilot_ttl_s" if role == "pilot" else "cognition_ttl_s"]
        request = role_request(self, role, obs)
        work = WorkItem(self.next_id, self.version, captured, captured+s_to_ns(ttl),
                        request, self.settings["stream_actions"])
        if role == "pilot":
            self.buffer.begin(work.request_id, self.version)
        self.pending = (work, obs)
        self.pending_depth = capture_depth(obs) if role == "direction" else None
        self.worker.submit(work)
        self.next_id += 1
        self.log("submitted", captured, request_id=work.request_id, role=role,
                 observation_seq=obs.seq, prompt=request.prompt, images=request.images)

    def receive(self, event, obs, now):
        kind = event["kind"]
        if kind == "fatal":
            self.failed = True
            self.pause("worker fatal", now)
            self.log("failure", now, error=event["payload"])
        elif kind == "action":
            packet = action_record(event["item"], event["payload"])
            packet["source_t_sim_ns"] = self.pending[1].t_sim_ns
            self.buffer.append(packet)
            self.log("action_received", now, packet=packet)
        elif kind == "result":
            self.apply_result(event, obs, now)
        elif kind == "done":
            self.log("done", now, request_id=event["item"].request_id, **event["payload"])
            if event["payload"]["status"] == "failed":
                self.failure(event["payload"]["error"], now)
            elif event["item"].request.role != "pilot" and now >= event["item"].expires_ns:
                self.failure("cognitive request expired", now)
            self.pending = None
            self.pending_depth = None
        elif kind == "discarded":
            self.log("discarded", now, request_id=event["item"].request_id)

    def apply_result(self, event, obs, now):
        work, source = self.pending
        if work.request_id != event["item"].request_id:
            raise RuntimeError("request/source mismatch")
        role, payload = work.request.role, event["payload"][0]
        self.log("result", now, request_id=work.request_id, role=role, payload=payload)
        try:
            if role in {"direction", "monitor"} and not self.pose_valid(source, obs):
                raise ValueError("pose drift while interpreting cognitive image")
            if role == "planner" and skills_active(self):
                accept_skill(self, payload, now)
            elif role == "planner":
                if self.planner_event:
                    accept_recovery(self, payload, now)
                else:
                    accept_plan(self, payload, now)
                    remember(self, "plan_committed", now, steps=self.steps)
            elif role == "direction":
                self.accept_goal(payload, source, work.observed_ns, now)
            elif role == "vla_line":
                accept_native_line(self, payload, source, now)
            elif role == "monitor":
                self.accept_monitor(parse_monitor(payload), obs, now)
        except (ValueError, KeyError, TypeError) as exc:
            self.failure(str(exc), now)

    def pose_valid(self, source, obs):
        return (source.position.distance_to(obs.position) <= self.settings["pose_drift_m"]
                and abs(math.degrees(angle_error(source.yaw_rad, obs.yaw_rad)))
                <= self.settings["pose_drift_deg"])

    def accept_goal(self, payload, source, captured, now):
        if self.skill is not None and self.skill["skill"] == "detect":
            detected(self, payload, source, now)
            return
        if self.settings.get("goal_mode") == "visual":
            payload = self.prepare_visual_goal(payload, source, captured, now)
            if payload is None:
                return
        if switch(self.settings, "verifier"):
            payload = validate_direction(self, payload)
        else:
            payload = unverified_direction(self, payload)
        position, yaw, terminal = interpret_goal(payload, source, self.origin, self.settings)
        self.version += 1
        self.goal = Goal(self.version, position, yaw, terminal,
                         captured+s_to_ns(self.settings["goal_ttl_s"]), source.seq)
        self.best_distance = self.best_heading = math.inf
        self.progress_at = self.last_monitor = now
        self.log("goal_authorized", now, position=position.model_dump(), yaw=yaw,
                 terminal=terminal, expires_ns=self.goal.expires_ns, source_seq=source.seq)

    def prepare_visual_goal(self, payload, source, captured, now):
        proposal = grounded_direction(payload)
        if proposal is None:
            self.target_absent(source, captured, now)
            return None
        self.log("grounding_validated", now, payload=proposal, source_seq=source.seq)
        near = record_grounding(self, proposal, source, captured, now)
        distance = self.visual_evidence["range_m"]
        remember_object(self, proposal, source, distance, now)
        if distance is not None:
            # Aim just inside the near range so the object stays in view, and keep
            # each leg longer than the arrival tolerance so it is never reached on issue.
            standoff = aim_standoff(self)
            min_travel = self.settings["position_m"] + MIN_LEG_MARGIN_M
            proposal["target"]["travel_m"] = min(self.settings["max_goal_m"],
                                                 max(min_travel, distance-standoff))
        if self.verify_visual_stop(proposal, source, now):
            return None
        if near:
            self.goal = Goal(self.version, source.position, source.yaw_rad, False,
                             captured+s_to_ns(self.settings["goal_ttl_s"]), source.seq)
            self.request_monitor("fresh object proximity; verify visual accomplishment", now)
            return None
        return proposal

    def target_absent(self, source, captured, now):
        self.visual_evidence = None
        if object_below(self, source, now):
            self.log("object_below_completion", now, source_seq=source.seq,
                     memory=self.object_memory["position"].model_dump())
            self.goal = Goal(self.version, source.position, source.yaw_rad, False,
                             captured+s_to_ns(self.settings["goal_ttl_s"]), source.seq)
            self.complete_visual(now)
            return
        if not self.target_missing:
            self.target_missing = True
            if self.search_authorized and search_allowed(self):
                start_search(self, now)
                self.log("grounding_absent", now, source_seq=source.seq)
                return
            self.request_planner("target_lost", now)
        self.pause("requested object not visible; no blind approach", now)
        self.hold_until = now+s_to_ns(self.settings["monitor_retry_s"])
        self.log("grounding_absent", now, source_seq=source.seq)

    def request_planner(self, trigger, now):
        if skills_active(self):
            skill_finished(self, trigger, now)  # the skill agent decides what to do next
            return
        self.visual_stop_pending = False
        remember(self, trigger, now, objective=self.plan, evidence=self.visual_evidence)
        self.replan(trigger, now)
        if self.steps and switch(self.settings, "recovery") != "none":
            self.planner_event = trigger
            self.log("planner_wakeup", now, trigger=trigger, step_index=self.step_index)

    def accept_monitor(self, monitor, obs, now):
        self.last_monitor = now
        self.monitor_reason = None
        status = monitor["status"]
        self.feedback = monitor["reason"]
        if status == "continue" and self.numeric_complete(obs):
            self.log("numeric_completion_override", now, model_status=status,
                     model_reason=self.feedback, remaining=self.goal.error(obs))
            status = "stop"
        if status == "hold" and self.near_and_settled(obs, now):
            status = "stop"  # fresh near evidence: the model's "hold" means stay here, not a hazard
        if status == "hold":
            self.pause("monitor hold: " + self.feedback, now)
            self.monitor_reason = "recheck held step"
            self.hold_until = now+s_to_ns(self.settings["monitor_retry_s"])
        elif status == "replan":
            self.request_planner("monitor_replan: " + self.feedback, now)
        elif status == "stop":
            self.accept_stop(obs, now)
        else:
            self.continue_mission(obs, now)

    def accept_stop(self, obs, now):
        settled = obs.velocity.norm() <= self.settings["stopped_mps"]
        if not self.goal.arrived(obs, self.settings) or not settled:
            self.pause("monitor stop rejected: arrival/heading/speed", now)
            self.log("stop_rejected", now, remaining=self.goal.error(obs))
        elif self.settings.get("goal_mode") == "visual":
            if fresh_evidence(self, obs, now):
                distance = self.visual_evidence["range_m"]
                if distance is not None and distance <= near_limit(self):
                    self.complete_visual(now)
                    return
            self.visual_stop_pending = True
            self.replan("verify visual stop with fresh grounding and depth", now)
        else:
            self.finish_step(now)

    def finish_step(self, now):
        if skills_active(self):
            skill_finished(self, "completed", now)
            return
        remember(self, "subgoal_completed", now, objective=self.plan)
        terminal = self.step_index == len(self.steps)-1 if self.steps else self.goal.terminal
        if terminal:
            self.stopped = True
            self.pause("monitor stop accepted", now)
        else:
            self.advance_mission(now)

    def verify_visual_stop(self, proposal, obs, now):
        if not self.visual_stop_pending:
            return False
        distance = observed_range(proposal, obs, self.pending_depth)
        near = distance is not None and distance <= near_limit(self)
        settled = obs.velocity.norm() <= self.settings["stopped_mps"]
        self.log("visual_stop_verification", now, range_m=distance,
                 limit_m=near_limit(self), accepted=near and settled, source_seq=obs.seq)
        self.visual_stop_pending = False
        if near and settled:
            self.complete_visual(now)
            return True
        return False

    def complete_visual(self, now):
        if hold_required_ns(self) and self.hold_started is None:
            start_hold(self, now)
        else:
            self.finish_step(now)

    def near_and_settled(self, obs, now):
        if not (self.steps and isinstance(self.plan["target"], str)) or self.goal is None:
            return False
        evidence = self.visual_evidence or {}
        distance = evidence.get("range_m") if fresh_evidence(self, obs, now) else None
        return (distance is not None and distance <= near_limit(self)
                and obs.velocity.norm() <= self.settings["stopped_mps"])

    def check_hold(self, obs, now):
        if now < self.hold_until:
            return
        settled = obs.velocity.norm() <= self.settings["stopped_mps"]
        evidence = self.visual_evidence or {}
        distance = evidence.get("range_m") if fresh_evidence(self, obs, now) else None
        near = distance is not None and distance <= near_limit(self)
        self.log("hold_check", now, range_m=distance, settled=settled,
                 object_below=object_below(self, obs, now))
        if settled and (near or object_below(self, obs, now)):
            self.hold_started = None
            self.finish_step(now)
        else:
            self.replan("hold interrupted: object no longer confirmed near", now)

    def continue_mission(self, obs, now):
        self.progress_at = now
        if (self.steps and isinstance(self.plan["target"], str)
                and self.goal.arrived(obs, self.settings)
                and obs.velocity.norm() <= self.settings["stopped_mps"]):
            self.log("visual_waypoint_refresh", now, objective=self.plan["objective"],
                     step_index=self.step_index)
            self.replan("visual waypoint reached; same objective needs fresh grounding", now)

    def numeric_complete(self, obs):
        return (bool(self.steps) and (isinstance(self.plan["target"], list)
                                     or world_target(self.plan["target"]))
                and self.goal.arrived(obs, self.settings)
                and obs.velocity.norm() <= self.settings["stopped_mps"])

    def advance_mission(self, now):
        self.completed = [*self.completed, dict(plan=self.plan, result=self.feedback)][-16:]
        if self.steps:
            self.step_index += 1
        self.replan("intermediate goal reached; advance mission", now)

    def check_events(self, obs, now):
        if self.goal is None or self.stopped or self.failed or self.monitor_reason:
            return
        if now >= self.goal.expires_ns:
            self.replan("persistent goal expired", now)
            return
        distance = obs.position.distance_to(self.goal.position)
        heading = abs(self.goal.error(obs)[-1])
        progressed = distance < self.best_distance-self.settings["progress_m"]
        progressed |= heading < self.best_heading-self.settings["progress_deg"]
        if progressed:
            self.best_distance, self.best_heading, self.progress_at = distance, heading, now
        elapsed = now-self.last_monitor
        retry_due = elapsed >= s_to_ns(self.settings["monitor_retry_s"])
        if self.goal.arrived(obs, self.settings) and retry_due:
            if self.settings.get("goal_mode") == "visual":
                self.continue_mission(obs, now)
            else:
                self.request_monitor("arrival", now)
        elif now-self.progress_at >= s_to_ns(self.settings["stall_s"]):
            self.request_planner("stalled_progress", now)
        else:
            self.periodic_checks(elapsed, now)

    def periodic_checks(self, elapsed, now):
        if recovery_due(self, now):
            self.last_recovery = now
            self.request_planner("periodic_review", now)
            return
        monitor = switch(self.settings, "monitor")
        visual_leg = bool(self.steps) and isinstance(self.plan["target"], str)
        # Visual evidence goes stale as soon as the drone moves, so by default a mid-leg
        # check can only answer replan; visual legs end in fresh grounding instead.
        if (monitor != "none" and elapsed >= s_to_ns(self.settings["monitor_interval_s"])
                and (monitor == "periodic" or not visual_leg)):
            self.request_monitor("periodic scene check", now)

    def failure(self, reason, now):
        self.failures += 1
        self.replan(reason, now)
        self.failed = self.failures >= self.settings["max_failures"]
        self.log("contract_failure", now, error=reason, count=self.failures)
