"""Two frozen C2/C3 visible-target preflights; no policy edits or retries."""

import argparse
import asyncio
import json
from pathlib import Path

from scripts.run_commitment_pair import DIGEST, api, write

from uavlab.core.compose import load_architecture, load_environment
from uavlab.core.config import EpisodeSpec
from uavlab.core.orchestrator import Orchestrator
from uavlab.experiments.manifest import build_manifest, write_manifest

OUT = Path("reports/c2_c3_preflight_20260916")


async def main(freeze):
    arches = {v: load_architecture(f"{v}_spf_qwen4_current_dev") for v in ["c2", "c3"]}
    env = load_environment("capability_visible_target_slow_240_dev")
    snapshot = dict(
        seed=1061,
        environment=env.model_dump(mode="json"),
        architectures={v: a.model_dump(mode="json") for v, a in arches.items()},
        order=["c2", "c3"],
        max_flights=2,
        max_sim_s=240,
        purpose="Visible-target model/stop preflight; no clutter or architecture ranking claim.",
    )
    if freeze:
        assert not (OUT / "FREEZE.json").exists()
        write(OUT / "FREEZE.json", snapshot)
        write(OUT / "STATE.json", dict(status="frozen", runs=[], active=None))
        return
    assert json.loads((OUT / "FREEZE.json").read_text(encoding="utf-8")) == snapshot
    for seed in [1060, 1062]:
        state = json.loads(
            Path(f"reports/commitment_validation_20260916/s{seed}/STATE.json").read_text(
                encoding="utf-8"
            )
        )
        assert len(state["runs"]) == 2 and state["active"] is None, "C5 batch must finish first"
    model = next(m for m in api("/api/ps")["models"] if m["name"] == "qwen3-vl:4b")
    assert model["digest"] == DIGEST and model["size_vram"] > 0
    write(OUT / "RESIDENCY_START.json", model)
    state = dict(status="running", runs=[], active=None)
    for variant, arch in arches.items():
        state["active"] = variant
        write(OUT / "STATE.json", state)
        name = f"{variant}_visible_preflight_20260916_s1061"
        out = Path("runs") / name
        assert not out.exists()
        write_manifest(build_manifest(arch, env, seeds=[1061]), out)
        runner = Orchestrator(
            arch, env, EpisodeSpec(episode_id=name, seed=1061), out_dir=out, debug_capture=True
        )
        result = await runner.run()
        write(out / "result.json", result.model_dump(mode="json"))
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
    state.update(status="flights_complete_audit_pending", active=None)
    write(OUT / "STATE.json", state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    asyncio.run(main(parser.parse_args().freeze))
