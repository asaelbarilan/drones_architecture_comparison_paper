"""Bounded D143 whole-architecture experiment with the D142 experimental pilot."""

import argparse
import asyncio
import hashlib
import json
import threading
from pathlib import Path

from classical_pilot_backend import ClassicalPilotBackend
from probe_qwen_fast_worker import ExperimentalBackend
from run_qwen_async import deadline_exit

from uavlab.live_qwen.prompts import DIRECTION, MONITOR, PLANNER
from uavlab.live_qwen.runner import await_worker, fly
from uavlab.plugins.inference.qwen_worker import QwenWorker


async def experiment(settings, out, flight=fly):
    options = dict(
        package_path=settings["package_path"], model_id=settings["model_id"],
        max_new_tokens=128, warmup_path=str(out / "startup_equality.json"),
        cpu_placement="performance", cpu_qos="latency", burst_capacity=256,
        prompt_audit=True)
    factory = ExperimentalBackend
    if settings.get("pilot_mode", "vla") == "classical":
        factory = ClassicalPilotBackend
        options.update({k: settings[k] for k in
                        ("action_duration_s", "max_speed_mps", "max_yaw_rate_rps")})
    worker = QwenWorker(options, factory=factory)
    worker.start()
    results = {}
    try:
        await await_worker(worker, settings, ready=True)
        for case in settings["missions"]:
            results[case["id"]] = await flight(worker, case, settings, out / case["id"])
            (out / "result.json").write_text(json.dumps(results, indent=2))
            print(json.dumps(results[case["id"]]), flush=True)
            await await_worker(worker, settings)
        return results
    finally:
        worker.close()


def provenance(out):
    paths = list(Path("src/uavlab/live_qwen").glob("*.py"))
    names = ("probe_qwen_fast_worker.py", "probe_qwen_decoder_graph.py",
             "qwen_action_burst_probe.py", "qwen_vision_graph_probe.py",
             "run_qwen_full_architecture.py")
    paths += [Path("scripts/diagnostics") / name for name in names]
    hashes = {p.as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (out / "source_hashes.json").write_text(json.dumps(hashes, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--config", type=Path,
                        default=Path("configs/experiments/qwen_async_local.json"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    settings = json.loads(args.config.read_text())
    settings["inference_kind"] = "real shared Qwen; experimental D142 full graphs"
    settings["experimental_burst_capacity"] = 256
    (args.out / "config.json").write_text(json.dumps(settings, indent=2))
    (args.out / "prompt_templates.json").write_text(json.dumps(
        dict(planner=PLANNER, direction=DIRECTION, monitor=MONITOR), indent=2))
    provenance(args.out)
    timer = threading.Timer(settings["watchdog_s"], deadline_exit)
    timer.daemon = True
    timer.start()
    try:
        asyncio.run(experiment(settings, args.out))
    except Exception as error:
        (args.out / "failure.json").write_text(json.dumps(dict(error=repr(error)), indent=2))
        raise
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
