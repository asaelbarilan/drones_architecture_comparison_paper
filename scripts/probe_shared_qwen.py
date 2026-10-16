"""Bounded-process caller should cap this local, no-flight D-132 probe."""

import asyncio
import base64
import faulthandler
import json
import os
import threading
import time
from pathlib import Path

from uavlab.contracts import (
    KinematicAction,
    MemorySnapshot,
    MissionSpec,
    PerceptionState,
    TaskFamily,
)
from uavlab.core.event_log import EventLog
from uavlab.core.feature_cache import FeatureCache
from uavlab.core.frame_store import global_store
from uavlab.core.registry import REGISTRY
from uavlab.core.services import RuntimeServices
from uavlab.interfaces import DecisionContext, InferenceRequest
from uavlab.plugins.inference.shared_qwen import SharedQwenInference
from uavlab.plugins.reasoning.shared_qwen_pilot import (
    DIRECTION,
    MONITOR,
    PLANNER,
    SharedQwenPilot,
    parse_direction,
    parse_monitor,
    parse_plan,
)

OUT = Path(os.environ.get("D132_OUTPUT", "reports/shared_qwen_vla_20261016/final"))


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "result.json").exists():
        raise RuntimeError("Preserve existing evidence: choose a fresh output directory")
    mission = MissionSpec(
        mission_id="d132-contract",
        instruction="Fly toward the red tower.",
        task_family=TaskFamily.LONG_HORIZON_NAV,
    )
    env = REGISTRY.build("environment", "grid3d", {"render": True, "render_depth": True})
    obs = await env.reset(mission, 1061)
    frame = global_store().get(obs.rgb.uri)
    frame.save(OUT / "input.png")
    encoded = base64.b64encode((OUT / "input.png").read_bytes()).decode()
    backend = SharedQwenInference(
        "D:/drone_vla_pilot/release/hf_fresh_d257/model", audit_path=OUT / "calls.jsonl"
    )
    results = {"scope": "four-role contract probe; no flight or efficacy claim", "seed": 1061}

    def req(role, prompt, image=True):
        return InferenceRequest(
            model_id=backend.model_id,
            role=role,
            prompt_hash="d132-probe",
            prompt=prompt,
            images=(encoded,) if image else (),
            image_count=int(image),
            observation_seq=obs.seq,
        )

    try:
        start = time.monotonic()
        base_request = req("planner", PLANNER + mission.instruction, False)
        first = await backend.invoke(base_request)

        def base_logits():
            with backend.model.disable_adapter(), backend.torch.inference_mode():
                batch = backend.api.cuda(backend._chat_batch(base_request))
                return backend.model(**batch, use_cache=False).logits[0, -1].float().cpu()

        original_logits = base_logits()
        results["planner"] = parse_plan(first.payload)
        direction = await backend.invoke(
            req("direction", DIRECTION + json.dumps(results["planner"]))
        )
        results["direction"] = parse_direction(direction.payload)
        monitor = await backend.invoke(
            req(
                "monitor",
                MONITOR
                + json.dumps(
                    {
                        "mission": mission.instruction,
                        "local_goal_remaining_fru_m_clockwise_deg": [2, 0, 0, 0],
                        "speed_mps": 0,
                    }
                ),
            )
        )
        results["monitor"] = parse_monitor(monitor.payload)
        # Fixed numeric fixture isolates the codec/switch contract from navigation.
        pilot = await backend.invoke(
            req(
                "pilot",
                json.dumps(
                    dict(
                        instruction="Move forward 2 meters.",
                        state=[0, 0, 0, 0],
                        remaining=[2, 0, 0, 0],
                        box=None,
                    )
                ),
            )
        )
        results["pilot"] = pilot.payload
        repeated = await backend.invoke(base_request)
        results["base_logits_exact_after_pilot"] = backend.torch.equal(
            original_logits, base_logits()
        )
        results["base_text_exact_after_pilot"] = first.payload == repeated.payload
        results["one_base_load"] = backend.load_count == 1
        results["peak_vram_bytes"] = backend.torch.cuda.max_memory_allocated()
        results["wall_seconds"] = time.monotonic() - start
        results["passed"] = all(
            results[k]
            for k in (
                "base_text_exact_after_pilot",
                "base_logits_exact_after_pilot",
                "one_base_load",
            )
        )
        if results["passed"]:
            await stepped_probe(backend, results)
    except Exception as exc:
        results.update(passed=False, error=f"{type(exc).__name__}: {exc}")
        raise
    finally:
        results["stats"] = backend.stats()
        (OUT / "result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        backend.close()


async def stepped_probe(backend, results):
    """Two real-policy steps; simulator explicitly paused during model calls.

    This tests wiring only. Wall latency remains in calls.jsonl; it does NOT
    validate real-time scheduling, staleness admission, or AirSim dynamics.
    """
    mission = MissionSpec(
        mission_id="d132-steps",
        instruction="Move forward 2 meters.",
        task_family=TaskFamily.LONG_HORIZON_NAV,
    )
    env = REGISTRY.build("environment", "grid3d", {"render": True, "render_depth": True})
    obs = await env.reset(mission, 1061)

    class PausedClock:
        ns = 0

        def now_ns(self):
            return self.ns

        def wall_ns(self):
            return time.perf_counter_ns()

    clock = PausedClock()
    policy = SharedQwenPilot()
    policy.bind_runtime(
        RuntimeServices(
            clock=clock,
            log=EventLog("d132-steps", None),
            feature_cache=FeatureCache(),
            inference=backend,
            episode_id="d132-steps",
        )
    )
    policy.reset(mission, 1061)
    controller = REGISTRY.build("controller", "mock_velocity")
    controller.reset(mission, 1061)
    rows = []
    for index in range(2):
        global_store().get(obs.rgb.uri).save(OUT / f"step_{index}.png")
        ctx = DecisionContext(
            mission=mission,
            observation=obs,
            perception=PerceptionState(observation_seq=obs.seq, t_sim_ns=obs.t_sim_ns),
            memory=MemorySnapshot(observation_seq=obs.seq, t_sim_ns=obs.t_sim_ns),
            t_sim_ns=obs.t_sim_ns,
            t_wall_ns=obs.t_wall_ns,
            episode_id="d132-steps",
        )
        clock.ns = obs.t_sim_ns
        decision = await policy.decide(ctx)
        row = {"before": obs.position.model_dump(), "decision": decision.model_dump(mode="json")}
        if isinstance(decision.payload, KinematicAction):
            command = controller.from_action(decision.payload, ctx, decision.decision_id)
            # Substep physics at 20 Hz; not one large displacement teleport.
            for _ in range(max(1, round(decision.payload.duration_s / 0.05))):
                await env.step(command, 50_000_000)
            obs = await env.observe()
            row["after"] = obs.position.model_dump()
        rows.append(row)
    results["stepped_simulator"] = {
        "mode": "paused during inference; no shield/router test",
        "steps": rows,
        "success_claim": False,
    }
    await env.close()


if __name__ == "__main__":
    faulthandler.dump_traceback_later(60, repeat=True)
    print("D132 probe starting", flush=True)
    watchdog = threading.Timer(600, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    asyncio.run(main())
    watchdog.cancel()
