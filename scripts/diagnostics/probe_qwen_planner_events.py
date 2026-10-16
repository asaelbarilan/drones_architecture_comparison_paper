"""Frozen-model replay of injected recovery events; no simulator motion."""

import argparse
import json
import os
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.interfaces import InferenceRequest
from uavlab.live_qwen.planner_memory import MEMORY_LIMIT, RECOVERY
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


def contexts(root):
    settings = json.loads((root / "config.json").read_text())
    rows = [json.loads(s) for s in (root / "red_pillar/events.jsonl").read_text().splitlines()]
    steps = next(r["steps"] for r in rows if r["kind"] == "mission_plan_committed")
    memory = [r["entry"] for r in rows if r["kind"] == "planner_memory"][-MEMORY_LIMIT:]
    for trigger, evidence in (("target_lost", "The requested target is no longer visible"),
                              ("stalled_progress", "Repeated movement made no progress"),
                              ("monitor_replan: unsafe", "The route is blocked; motion is unsafe")):
        yield dict(original_mission=settings["missions"][0]["instruction"],
                   committed_steps=steps, active_step=0, completed_steps=[], trigger=trigger,
                   observations=[*memory, dict(event=trigger, evidence=evidence)],
                   feedback=evidence, diagnostic="injected replay, not observed flight event")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    backend = SharedQwenInference("D:/drone_vla_pilot/release/hf_fresh_d257/model")
    rows = []
    try:
        for context in contexts(args.root):
            request = InferenceRequest(model_id=backend.model_id, role="planner",
                                       prompt_hash="d148-event-probe",
                                       prompt=RECOVERY+json.dumps(context))
            payload, tokens = backend._run(request)
            rows.append(dict(context=context, prompt=request.prompt,
                             response=payload, tokens=tokens))
            (args.root.parent / "planner_event_probe.json").write_text(json.dumps(rows, indent=2))
            print(json.dumps(dict(trigger=context["trigger"], response=payload)), flush=True)
    finally:
        backend.close()


if __name__ == "__main__":
    main()
