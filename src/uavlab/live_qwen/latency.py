"""Non-executing startup probe; a model load alone is not latency readiness."""

import asyncio
import json
import time

from uavlab.contracts import s_to_ns
from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.qwen_worker import WorkItem

from .prompts import image_text

WARM_REPEATS = 3
PROBE_VERSION = -2
DRAIN_SECONDS = 10


def diagnostic_request(obs, settings):
    """A held camera input for timing only, never a flight command or task oracle."""
    return InferenceRequest(model_id=settings["model_id"], role="pilot",
                            prompt_hash="d136:nonexecuting-startup",
                            prompt=json.dumps(dict(instruction="Hold position.", state=[0]*4,
                                                   remaining=[0]*4, box=None)),
                            images=(image_text(obs),), image_count=1, observation_seq=obs.seq)


async def sample(worker, request, settings):
    started = time.perf_counter_ns()
    expires = started+s_to_ns(settings["pilot_ttl_s"])
    item = WorkItem(worker.last_id+1, PROBE_VERSION, started, expires, request, 1)
    worker.submit(item)
    delivery = None
    status = None
    while time.perf_counter_ns() < expires+s_to_ns(DRAIN_SECONDS):
        now = time.perf_counter_ns()
        for event in worker.poll(PROBE_VERSION, now):
            if event["kind"] == "fatal":
                raise RuntimeError(event["payload"])
            if event["kind"] == "action":
                delivery = (now-started)/1e9
            if event["kind"] == "done":
                status = event["payload"]["status"]
        if worker.current is None:
            return dict(first_action_s=delivery, status=status, request_id=item.request_id)
        await asyncio.to_thread(time.sleep, 1/settings["control_hz"])
    worker.revoke()
    raise TimeoutError("latency probe did not drain")


async def qualify(worker, request, settings, record):
    """Discard one bounded warmup, require three timely complete warm requests."""
    rows = []
    limit = settings["pilot_ttl_s"]-1/settings["control_hz"]
    record(dict(kind="latency_input", request_id=f"preflight_{worker.last_id+1}",
                prompt=request.prompt, images=request.images, execution_allowed=False))
    for index in range(WARM_REPEATS+1):
        row = await sample(worker, request, settings)
        record(dict(kind="latency_probe", index=index, execution_allowed=False,
                    max_first_action_s=limit, **row))
        rows.append(row)
        if row["status"] not in {"complete", "cancelled"}:
            raise RuntimeError("latency preflight inference failed")
        if index and (row["status"] != "complete" or row["first_action_s"] is None
                      or row["first_action_s"] >= limit):
            raise RuntimeError("latency preflight failed; flight not started")
    return rows
