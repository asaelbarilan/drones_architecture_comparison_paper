"""Event-driven role scheduler: persistent goals, one GPU owner, no control waits."""

import math

from uavlab.contracts import s_to_ns
from uavlab.plugins.inference.action_buffer import ActionBuffer, action_record
from uavlab.plugins.inference.qwen_worker import WorkItem
from uavlab.plugins.reasoning.shared_qwen_pilot import parse_monitor

from .goals import Goal, angle_error, interpret_goal
from .grounding import NEAR_OBJECT_M, capture_depth, grounded_direction, observed_range
from .mission_plan import accept_plan, validate_direction
from .prompts import role_request


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
        self.pause(reason, now)
        self.monitor_reason = reason

    def replan(self, reason, now):
        self.pause(reason, now)
        self.version += 1
        self.plan = self.goal = None
        if self.steps:
            self.plan = dict(self.steps[self.step_index])
        self.monitor_reason = None
        self.feedback = reason
        self.log("replan", now, reason=reason)

    def update(self, obs, captured_ns, now, moving):
        if self.origin is None:
            self.origin, self.last_yaw = obs, obs.yaw_rad
            self.progress_at = self.last_monitor = now
        self.yaw_total += angle_error(obs.yaw_rad, self.last_yaw)
        self.last_yaw = obs.yaw_rad
        for event in self.worker.poll(self.version, now):
            self.receive(event, obs, now)
        self.check_events(obs, now)
        if now < self.hold_until:
            return
        if self.stopped or self.failed or self.worker.current is not None:
            return
        role = self.next_role(obs, moving)
        if role:
            self.submit(role, obs, captured_ns)

    def next_role(self, obs, moving):
        if self.monitor_reason:
            return "monitor" if obs.velocity.norm() <= self.settings["stopped_mps"] else None
        if self.plan is None:
            return "planner"
        if self.goal is None:
            return "direction" if obs.velocity.norm() <= self.settings["stopped_mps"] else None
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
            if role == "planner":
                accept_plan(self, payload, now)
            elif role == "direction":
                self.accept_goal(payload, source, work.observed_ns, now)
            elif role == "monitor":
                self.accept_monitor(parse_monitor(payload), obs, now)
        except (ValueError, KeyError, TypeError) as exc:
            self.failure(str(exc), now)

    def pose_valid(self, source, obs):
        return (source.position.distance_to(obs.position) <= self.settings["pose_drift_m"]
                and abs(math.degrees(angle_error(source.yaw_rad, obs.yaw_rad)))
                <= self.settings["pose_drift_deg"])

    def accept_goal(self, payload, source, captured, now):
        if self.settings.get("goal_mode") == "visual":
            payload = grounded_direction(payload)
            if payload is None:
                self.pause("requested object not visible; no blind approach", now)
                self.hold_until = now+s_to_ns(self.settings["monitor_retry_s"])
                self.log("grounding_absent", now, source_seq=source.seq)
                return
            self.log("grounding_validated", now, payload=payload, source_seq=source.seq)
            if self.verify_visual_stop(payload, source, now):
                return
        payload = validate_direction(self, payload)
        position, yaw, terminal = interpret_goal(payload, source, self.origin, self.settings)
        self.version += 1
        self.goal = Goal(self.version, position, yaw, terminal,
                         captured+s_to_ns(self.settings["goal_ttl_s"]), source.seq)
        self.best_distance = self.best_heading = math.inf
        self.progress_at = self.last_monitor = now
        self.log("goal_authorized", now, position=position.model_dump(), yaw=yaw,
                 terminal=terminal, expires_ns=self.goal.expires_ns, source_seq=source.seq)

    def accept_monitor(self, monitor, obs, now):
        self.last_monitor = now
        self.monitor_reason = None
        status = monitor["status"]
        self.feedback = monitor["reason"]
        if status == "continue" and self.numeric_complete(obs):
            self.log("numeric_completion_override", now, model_status=status,
                     model_reason=self.feedback, remaining=self.goal.error(obs))
            status = "stop"
        if status == "hold":
            self.pause("monitor hold: " + self.feedback, now)
            self.monitor_reason = "recheck held step"
            self.hold_until = now+s_to_ns(self.settings["monitor_retry_s"])
        elif status == "replan":
            self.replan(f"monitor {status}: {self.feedback}", now)
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
            self.visual_stop_pending = True
            self.replan("verify visual stop with fresh grounding and depth", now)
        else:
            self.finish_step(now)

    def finish_step(self, now):
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
        near = distance is not None and distance <= NEAR_OBJECT_M
        settled = obs.velocity.norm() <= self.settings["stopped_mps"]
        self.log("visual_stop_verification", now, range_m=distance,
                 limit_m=NEAR_OBJECT_M, accepted=near and settled, source_seq=obs.seq)
        self.visual_stop_pending = False
        if near and settled:
            self.finish_step(now)
            return True
        return False

    def continue_mission(self, obs, now):
        self.progress_at = now
        if (self.steps and isinstance(self.plan["target"], str)
                and self.goal.arrived(obs, self.settings)
                and obs.velocity.norm() <= self.settings["stopped_mps"]):
            self.log("visual_waypoint_refresh", now, objective=self.plan["objective"],
                     step_index=self.step_index)
            self.replan("visual waypoint reached; same objective needs fresh grounding", now)

    def numeric_complete(self, obs):
        return (bool(self.steps) and isinstance(self.plan["target"], list)
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
            self.request_monitor("arrival", now)
        elif now-self.progress_at >= s_to_ns(self.settings["stall_s"]):
            self.request_monitor("stalled progress", now)
        elif elapsed >= s_to_ns(self.settings["monitor_interval_s"]):
            self.request_monitor("periodic scene check", now)

    def failure(self, reason, now):
        self.failures += 1
        self.replan(reason, now)
        self.failed = self.failures >= self.settings["max_failures"]
        self.log("contract_failure", now, error=reason, count=self.failures)
