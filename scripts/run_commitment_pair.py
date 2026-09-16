"""Two fresh local flights with a matched240s budget; production runtime unchanged."""

import argparse
import asyncio
import json
import math
import urllib.request
from pathlib import Path

from uavlab.contracts import EventType, TerminationReason
from uavlab.core.compose import load_architecture, load_environment
from uavlab.core.config import EpisodeSpec
from uavlab.core.orchestrator import Orchestrator
from uavlab.experiments.manifest import build_manifest, write_manifest

OUT = Path("reports/commitment_pair_20260916")
VARIANTS = {"off": "c5_target_commitment_off_qwen4_dev", "on": "c5_target_commitment_qwen4_dev"}
DIGEST = "1343d82ebee38e26a4dd6b0180b915eb91550184e67c505dea97509571c8f683"


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    temp.replace(path)


def api(path):
    return json.load(urllib.request.urlopen("http://127.0.0.1:11435" + path, timeout=10))


def repetition(controls, proposals, now):
    """Conservative diagnostic censorship; no goal truth, no planner intervention."""
    start = now - 45
    controls = [r for r in controls if r["t"] >= start]
    proposals = [r for r in proposals if r["t"] >= start]
    if now < 45 or not controls or controls[0]["t"] > start + 0.051 or len(proposals) < 15:
        return False
    if any(abs(r["yaw_rate"]) > 0.01 for r in controls):
        return False
    if any(math.dist(r["position"], controls[0]["position"]) > 0.5 for r in controls):
        return False
    first = proposals[0]
    return all(
        r["kind"] == first["kind"] and math.dist(r["goal"], first["goal"]) <= 0.5 for r in proposals
    )


class ObservedRun(Orchestrator):
    def __init__(self, *args, variant, **kwargs):
        super().__init__(*args, **kwargs)
        self.variant = variant
        self.last_check = -1
        self.early_stop = False
        self.residencies = []

    def _check_termination(self):
        if super()._check_termination():
            return True
        now = self.clock.now_ns() / 1e9
        if int(now) == self.last_check:
            return False
        self.last_check = int(now)
        controls = [
            dict(
                t=e.t_sim_ns / 1e9,
                position=[e.payload[k] for k in ["position_x", "position_y", "position_z"]],
                yaw_rate=e.payload["yaw_rate"],
            )
            for e in self.log.of_type(EventType.CONTROL)
            if e.t_sim_ns / 1e9 >= now - 45
        ]
        proposals = []
        for e in self.log.of_type(EventType.DECISION_PROPOSED):
            p = e.payload
            if e.t_sim_ns / 1e9 < now - 45 or "source_observation_seq" not in p:
                continue
            target = p.get("decision_payload", {}).get("target")
            if target:
                proposals.append(
                    dict(
                        t=e.t_sim_ns / 1e9,
                        kind=p["provenance"].get("waypoint_kind"),
                        goal=[target[k] for k in ["x", "y", "z"]],
                    )
                )
        self.early_stop = repetition(controls, proposals, now)
        write(
            OUT / f"{self.variant}_progress.json",
            dict(
                t=now,
                position=controls[-1]["position"],
                repeated_failure=self.early_stop,
                policy_proposals_in_window=len(proposals),
            ),
        )
        if int(now) % 30 == 2:
            resident = api("/api/ps")
            model = next(m for m in resident["models"] if m["name"] == "qwen3-vl:4b")
            assert model["digest"] == DIGEST and model["size_vram"] > 0, "GPU residency changed"
            self.residencies.append(dict(t=now, model=model))
            write(OUT / f"{self.variant}_residency.json", self.residencies)
        if self.early_stop:
            self._finish(
                TerminationReason.TIMEOUT,
                "diagnostic early stop:45s stationary/no turn/repeated goals; censored",
            )
            return True
        return False


def configs():
    arches = {k: load_architecture(v) for k, v in VARIANTS.items()}
    a, b = [arches[k].model_dump(mode="json") for k in ["off", "on"]]
    for d in [a, b]:
        for key in ["id", "name", "description"]:
            d.pop(key)
    assert a["policy"]["params"]["target_commitment_s"] == 0
    assert b["policy"]["params"]["target_commitment_s"] == 20
    a["policy"]["params"]["target_commitment_s"] = 20
    assert a == b, "unmatched architecture settings"
    env = load_environment("grid_nav_clutter_240_dev")
    assert env.max_episode_s == 240 and env.params["success"]["max_flight_time_s"] == 240
    return arches, env


async def main(args):
    arches, env = configs()
    if args.freeze:
        write(
            OUT / "FREEZE.json",
            dict(
                seed=1061,
                order=["off", "on"],
                environment=env.model_dump(mode="json"),
                architectures={k: v.model_dump(mode="json") for k, v in arches.items()},
                criteria="One fresh flight per variant; same240s budget. LocalQwen GPU. "
                "Only commitment0/20 differs. Preserve all results. Stop on native termination "
                "or45s stationary within0.5m, yaw<=0.01rad/s, >=15 proposals all same kind "
                "and goals within0.5m. Such early stops are diagnostic censorship, "
                "not240s failures.",
                inference="Dedicated11435 GPU, one model, no shared11434/Valley mutations. "
                "temperature0 seed0 fixed policy1s/monitor1.2s simulation latency. "
                "Record realized prefix divergence and do not assume deterministic model outputs.",
                max_new_flights=2,
            ),
        )
        write(
            OUT / "STATE.json",
            dict(status="frozen", next="Start dedicatedGPU server and matched pair", runs=[]),
        )
        return
    frozen = json.loads((OUT / "FREEZE.json").read_text(encoding="utf-8"))
    assert frozen["environment"] == env.model_dump(mode="json")
    model = next(m for m in api("/api/tags")["models"] if m["name"] == "qwen3-vl:4b")
    assert model["digest"] == DIGEST
    write(OUT / "MODEL.json", model)
    state = dict(status="running", runs=[])
    for variant in ["off", "on"]:
        arch = arches[variant]
        assert arch.model_dump(mode="json") == frozen["architectures"][variant]
        name = f"c5_commitment_{variant}_240_20260916_s1061"
        out = Path("runs") / name
        assert not out.exists(), f"Run already exists:{out}"
        state["active"] = variant
        write(OUT / "STATE.json", state)
        write_manifest(build_manifest(arch, env, seeds=[1061]), out)
        runner = ObservedRun(
            arch,
            env,
            EpisodeSpec(episode_id=name, seed=1061),
            out_dir=out,
            debug_capture=True,
            variant=variant,
        )
        result = await runner.run()
        write(out / "result.json", result.model_dump(mode="json"))
        state["runs"].append(
            dict(
                variant=variant,
                run=name,
                success=result.success,
                termination=result.termination_reason.value,
                censored=runner.early_stop,
                sim_s=result.sim_duration_s,
                final_m=result.metrics["distance_to_goal_m"],
                error=result.error,
            )
        )
        write(OUT / "STATE.json", state)
        assert result.error is None, result.error
    state["status"] = "flights_complete_audit_pending"
    state["active"] = None
    write(OUT / "STATE.json", state)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    asyncio.run(main(parser.parse_args()))
