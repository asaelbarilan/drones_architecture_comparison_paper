"""Same shared Qwen backend, but pilot requests are flown by the classical controller.

Planner, grounding and monitor still run on the shared model in the same worker
and queue; only stream_pilot changes. Startup equivalence checks still exercise
the real VLA pilot, because the classical path is enabled only after loading.
"""

import time

from probe_qwen_fast_worker import ExperimentalBackend

from uavlab.live_qwen.classical_pilot import classical_payload

NO_TOKENS = [-1, -1, -1, -1]  # actions carry no model tokens; keeps the buffer's 4-channel check


class ClassicalPilotBackend(ExperimentalBackend):
    def __init__(self, package_path, warmup_path, **options):
        self.step_s = options.pop("action_duration_s")
        self.max_speed_mps = options.pop("max_speed_mps")
        self.max_yaw_rate_rps = options.pop("max_yaw_rate_rps")
        self.classical_ready = False
        super().__init__(package_path, warmup_path, **options)

    def _load(self):
        # stream_pilot calls _load per request, including inside the startup
        # equivalence check; only the outermost (actual) load may enable classical.
        loading = self.model is None
        super()._load()
        if loading:
            self.classical_ready = True

    def stream_pilot(self, request, delivery):
        if not self.classical_ready:
            return super().stream_pilot(request, delivery)
        if request.role != "pilot" or request.model_id != self.model_id:
            raise ValueError("pilot stream requires matching role/model")
        payload = classical_payload(request.prompt, delivery.actions, self.step_s,
                                    self.max_speed_mps, self.max_yaw_rate_rps)
        started = time.perf_counter_ns()
        for index, step in enumerate(payload["steps_fru_m_yaw_rad"]):
            if delivery.cancelled():
                break
            delivery.emit(dict(index=index, tokens=list(NO_TOKENS), step_fru_m_yaw_rad=step,
                               ready_ns=time.perf_counter_ns(), first_token_ns=started))
        return payload, 0
