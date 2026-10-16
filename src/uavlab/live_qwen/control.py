"""Consume streaming actions through the existing controller and independent shield."""

from uavlab.contracts import MemorySnapshot, PerceptionState, s_to_ns
from uavlab.core.registry import REGISTRY
from uavlab.interfaces import DecisionContext
from uavlab.plugins.reasoning.shared_qwen_pilot import pilot_action


def context(mission, obs, now):
    return DecisionContext(
        mission=mission, observation=obs, t_sim_ns=obs.t_sim_ns, t_wall_ns=now,
        episode_id=mission.mission_id,
        perception=PerceptionState(observation_seq=obs.seq, t_sim_ns=obs.t_sim_ns),
        memory=MemorySnapshot(observation_seq=obs.seq, t_sim_ns=obs.t_sim_ns),
    )


class LiveControl:
    def __init__(self, scheduler, settings, seed):
        self.scheduler, self.settings = scheduler, settings
        self.controller = REGISTRY.build("controller", **settings["controller"])
        self.shield = REGISTRY.build("shield", **settings["shield"])
        for component in (self.controller, self.shield):
            component.reset(scheduler.mission, seed)
        self.active = None
        self.until = 0
        self.epoch = 0

    def moving(self, now):
        return self.active is not None and now < self.until

    def tick(self, obs, captured, now):
        state = self.scheduler
        state.update(obs, captured, now, self.moving(now))
        ctx = context(state.mission, obs, now)
        if self.epoch != state.motion_epoch:
            self.active = None
            self.epoch = state.motion_epoch
        hold = bool(state.failed or state.stopped or state.monitor_reason or state.goal is None)
        hold |= state.goal is not None and state.goal.arrived(obs, self.settings)
        if hold:
            self.active = None
        elif not self.moving(now):
            self.active = None
            packet = state.buffer.take(state.version, now)
            if packet is not None:
                self.activate(packet, ctx, now)
        command = self.active if self.moving(now) else self.controller.hold(ctx)
        command, safety = self.shield.check(command, ctx)
        if safety.modified:
            state.log("shield", now, reason=safety.reason, proposed_active=self.active is not None)
            state.request_monitor("shield intervention: " + safety.reason, now)
            self.active = None
            command = self.controller.hold(ctx)
        return command

    def activate(self, packet, ctx, now):
        c = self.settings
        action = pilot_action(packet["step_fru_m_yaw_rad"], ctx.observation.yaw_rad,
                              c["action_duration_s"], c["max_speed_mps"], c["max_yaw_rate_rps"])
        self.until = min(now+s_to_ns(action.duration_s), packet["expires_ns"])
        identity = f"live:{packet['request_id']}:{packet['index']}"
        command = self.controller.from_action(action, ctx, identity)
        self.active = command.model_copy(update=dict(
            expires_t_sim_ns=ctx.t_sim_ns+self.until-now,
            source_observation_seq=packet["observation_seq"],
            source_t_sim_ns=packet["source_t_sim_ns"],
        ))
        self.scheduler.log("action_consumed", now, packet=packet, until_ns=self.until,
                           command=self.active.model_dump(mode="json"))
