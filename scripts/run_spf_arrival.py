"""Freeze and run two D-129 arrival preflights, never overwrite or retry a run."""

import argparse
import asyncio
import json
from pathlib import Path

from scripts.local_inference_resources import check_headroom
from scripts.local_inference_resources import snapshot as resource_snapshot
from scripts.run_commitment_pair import DIGEST, api, write

from uavlab.core.compose import load_architecture, load_environment
from uavlab.core.config import EpisodeSpec
from uavlab.core.orchestrator import Orchestrator
from uavlab.experiments.manifest import build_manifest, write_manifest

OUT = Path("reports/spf_arrival_20260917")


class AuditedRun(Orchestrator):
    def _check_termination(self):
        done = super()._check_termination()
        now = self.clock.now_ns() / 1e9
        if int(now) != getattr(self, "_progress_second", -1):
            self._progress_second = int(now)
            write(OUT / "PROGRESS.json", dict(run=self.episode.episode_id, t=now, done=done))
        return done


async def main(freeze, replacement=False):
    global OUT
    if replacement:
        OUT = Path("reports/spf_arrival_retry_20260917")
    arches = {v: load_architecture(f"{v}_spf_rgbd_arrival_qwen4_dev") for v in ["c2", "c3"]}
    env = load_environment("capability_visible_target_slow_240_dev")
    snapshot = dict(
        decision="D-129",
        seed=1061,
        environment=env.model_dump(mode="json"),
        architectures={v: a.model_dump(mode="json") for v, a in arches.items()},
        order=["c2", "c3"],
        max_flights=2,
        max_sim_s=240,
        hypotheses=[
            "Separate localization/depth can produce arrival despite wrong travel labels.",
            "Braking hold permits low-speed STOP before confirmed target evidence expires.",
        ],
        success=(
            "Unchanged task score: terminal STOP within2m goal center, plus measured "
            "terminal speed<=0.15m/s; no collision/bounds failure."
        ),
        limitations=(
            "Surface radius1m is a development margin, not a mathematical guarantee "
            "of center-radius2m. Extra model calls and bounded policy state change "
            "the architecture; no native SPF or isolated latency comparison claim."
        ),
        stop_rule="At most two flights; preserve failures; no automatic retry or broad sweep.",
    )
    if replacement:
        snapshot["decision"] = "D-131"
        snapshot["replaces_infrastructure_attempt"] = "c2_spf_arrival_20260917_s1061"
        snapshot["retry_rationale"] = (
            "D-129 ended before arrival due to image-encode allocation failure. "
            "Keep that attempt; same navigation code/configs, fresh IDs, "
            "pre-load and loaded headroom gates. No further automatic retries."
        )
    if freeze:
        assert not (OUT / "FREEZE.json").exists()
        write(OUT / "FREEZE.json", snapshot)
        write(OUT / "STATE.json", dict(status="frozen", runs=[], active=None))
        return
    assert json.loads((OUT / "FREEZE.json").read_text(encoding="utf-8")) == snapshot
    state = json.loads((OUT / "STATE.json").read_text(encoding="utf-8"))
    assert state["status"] == "frozen", "No implicit restart"
    resources = check_headroom(resource_snapshot(), loaded=True)
    write(OUT / "RESOURCE_START.json", resources)
    if not resources["ready"]:
        raise RuntimeError("Insufficient loaded-model headroom; no flight started")
    model = next(m for m in api("/api/ps")["models"] if m["name"] == "qwen3-vl:4b")
    assert model["digest"] == DIGEST and model["size"] == model["size_vram"]
    write(OUT / "RESIDENCY_START.json", model)
    for variant, arch in arches.items():
        resources = check_headroom(resource_snapshot(), loaded=True)
        write(OUT / f"RESOURCE_{variant}.json", resources)
        if not resources["ready"]:
            state.update(status="waiting_for_resources", active=None)
            write(OUT / "STATE.json", state)
            raise RuntimeError("Insufficient memory before next flight")
        state.update(status="running", active=variant)
        write(OUT / "STATE.json", state)
        suffix = "retry_20260917" if replacement else "20260917"
        name = f"{variant}_spf_arrival_{suffix}_s1061"
        dest = Path("runs") / name
        assert not dest.exists()
        write_manifest(build_manifest(arch, env, seeds=[1061]), dest)
        runner = AuditedRun(
            arch, env, EpisodeSpec(episode_id=name, seed=1061), out_dir=dest, debug_capture=True
        )
        result = await runner.run()
        write(dest / "result.json", result.model_dump(mode="json"))
        state["runs"].append(
            dict(
                variant=variant,
                run=name,
                success=result.success,
                sim_s=result.sim_duration_s,
                termination=result.termination_reason.value,
                final_m=result.metrics["distance_to_goal_m"],
                error=result.error,
            )
        )
        write(OUT / "STATE.json", state)
        assert result.error is None, result.error
        model = next(m for m in api("/api/ps")["models"] if m["name"] == "qwen3-vl:4b")
        assert model["digest"] == DIGEST and model["size"] == model["size_vram"]
        write(OUT / f"RESIDENCY_{variant}.json", model)
    state.update(status="flights_complete_audit_pending", active=None)
    write(OUT / "STATE.json", state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--replacement", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.freeze, args.replacement))
