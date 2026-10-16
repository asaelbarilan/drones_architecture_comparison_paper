"""One-time D134 saved-frame streaming/latency probe; no flight or training."""

from __future__ import annotations

import argparse
import base64
import io
import json
import os
import threading
import time
from itertools import pairwise
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.action_buffer import ActionBuffer, action_record
from uavlab.plugins.inference.action_stream import StreamOptions
from uavlab.plugins.inference.qwen_actions import ACTION_CHANNELS, CHUNK_ACTIONS
from uavlab.plugins.inference.qwen_worker import QwenWorker, WorkItem
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

NS_PER_SECOND = 1_000_000_000
MODES = ("original", "stream_chunk", "first_action")


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def requests(config, image_path, model_id):
    from PIL import Image, ImageEnhance

    source = Image.open(image_path).convert("RGB")
    result = []
    for seq, case in enumerate(config["cases"]):
        image = ImageEnhance.Brightness(source).enhance(case["brightness"])
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        result.append(InferenceRequest(
            model_id=model_id, role="pilot", prompt_hash="d134-saved-frame",
            prompt=json.dumps(dict(
                instruction=case["instruction"], state=[0] * ACTION_CHANNELS,
                remaining=case["remaining"], box=None,
            )),
            images=(base64.b64encode(buffer.getvalue()).decode(),),
            image_count=1, observation_seq=seq,
        ))
    return result


def measure(backend, request, mode):
    backend.torch.cuda.synchronize()
    start = time.perf_counter_ns()
    records = []
    if mode == "original":
        payload, _ = backend._run(request)
    else:
        actions = 1 if mode == "first_action" else CHUNK_ACTIONS
        payload, _ = backend.stream_pilot(
            request, StreamOptions(actions, records.append, lambda: False)
        )
    backend.torch.cuda.synchronize()
    elapsed = (time.perf_counter_ns() - start) / NS_PER_SECOND
    return dict(
        mode=mode, seconds=elapsed, tokens=payload["tokens"],
        actions=payload["steps_fru_m_yaw_rad"], stream=records,
        first_action_s=(records[0]["ready_ns"] - start) / NS_PER_SECOND if records else None,
        first_token_s=(records[0]["first_token_ns"] - start) / NS_PER_SECOND if records else None,
    )


def compare(rows):
    original = rows["original"]
    stream, first = rows["stream_chunk"], rows["first_action"]
    stream_tokens = [t for packet in stream["stream"] for t in packet["tokens"]]
    return dict(
        whole_tokens_equal=original["tokens"] == stream["tokens"] == stream_tokens,
        whole_actions_equal=original["actions"] == stream["actions"],
        first_tokens_equal=original["tokens"][:ACTION_CHANNELS] == first["tokens"],
        first_action_equal=original["actions"][:1] == first["actions"],
        streamed_before_end=stream["first_action_s"] < stream["seconds"],
    )


def run_pairs(backend, inputs, config, out):
    pairs = []
    for repeat in range(config["repeats"]):
        for case, request in enumerate(inputs):
            order = MODES[repeat:] + MODES[:repeat]
            rows = {mode: measure(backend, request, mode) for mode in order}
            checks = compare(rows)
            pairs.append(dict(case=case, repeat=repeat, rows=rows, checks=checks))
            save(out / "pairs.json", pairs)
            print(json.dumps(dict(case=case, repeat=repeat, checks=checks,
                                  seconds={m: r["seconds"] for m, r in rows.items()})), flush=True)
    return pairs


def model_probe(args, config):
    backend = SharedQwenInference(str(args.package))
    try:
        backend._load()
        versions = [(n, p._version) for n, p in backend.model.named_parameters()]
        inputs = requests(config, args.image, backend.model_id)
        language = InferenceRequest(model_id=backend.model_id, role="monitor", prompt_hash="test",
                                    prompt="Reply with exactly one word: ready.")
        before, _ = backend._run(language)
        backend._run(inputs[0])  # Warm-up is excluded from timing comparisons.
        pairs = run_pairs(backend, inputs, config, args.out)
        after, _ = backend._run(language)
        base_config = backend.model.get_base_model().config
        return dict(
            pairs=pairs, model_loads=backend.load_count, base_text_equal=before == after,
            tensor_versions_unchanged=versions == [(n, p._version)
                                                 for n, p in backend.model.named_parameters()],
            all_frozen=all(not p.requires_grad for p in backend.model.parameters()),
            peak_allocated_bytes=backend.torch.cuda.max_memory_allocated(),
            peak_reserved_bytes=backend.torch.cuda.max_memory_reserved(),
            text_attention=base_config.text_config._attn_implementation,
            vision_attention=base_config.vision_config._attn_implementation,
            transformers_version=__import__("transformers").__version__,
        )
    finally:
        backend.close()


def consume(events, buffer, records):
    for event in events:
        if event["kind"] == "fatal":
            raise RuntimeError(event["payload"])
        if event["kind"] == "action":
            record = action_record(event["item"], event["payload"])
            buffer.append(record)
            records.append(record)
        if event["kind"] == "done":
            records.append(dict(lifecycle=event["payload"]))


def pump(worker, buffer, config, finished):
    end = time.perf_counter() + config["worker_ready_timeout_s"]
    next_tick = time.perf_counter()
    ticks, records, consumed = [], [], []
    while time.perf_counter() < end:
        now = time.perf_counter_ns()
        ticks.append(now)
        consume(worker.poll(1, now), buffer, records)
        action = buffer.take(1, time.perf_counter_ns())
        if action is not None:
            consumed.append(dict(action, consumed_ns=time.perf_counter_ns()))
        if finished():
            break
        next_tick += 1 / config["control_hz"]
        time.sleep(max(0, next_tick - time.perf_counter()))
    else:
        raise TimeoutError("worker probe deadline")
    gaps = [(b - a) / NS_PER_SECOND for a, b in pairwise(ticks)]
    return dict(ticks=len(ticks), max_tick_gap_s=max(gaps, default=0),
                records=records, consumed=consumed)


def worker_probe(args, config):
    worker = QwenWorker(dict(package_path=str(args.package)))
    buffer = ActionBuffer()
    worker.start()
    try:
        startup = pump(worker, buffer, config, lambda: worker.ready)
        request = requests(config, args.image, "qwen3-vl-4b-d207-shared")[0]
        results = []
        for request_id, count in enumerate((1, CHUNK_ACTIONS)):
            now = time.perf_counter_ns()
            work = WorkItem(request_id, 1, now,
                            now + int(config["observation_ttl_s"] * NS_PER_SECOND), request, count)
            buffer.begin(request_id, 1)
            worker.submit(work)
            results.append(pump(worker, buffer, config, lambda: worker.current is None))
        return dict(startup=startup, calls=results, worker_pid=worker.process.pid)
    finally:
        worker.close()


def worker_checks(result, config):
    first, chunk = result["worker"]["calls"]
    expected = result["model"]["pairs"][0]["rows"]["original"]["tokens"]
    calls = (first, chunk)
    return dict(
        first_complete=first["records"][-1]["lifecycle"]["status"] == "complete",
        chunk_expires=chunk["records"][-1]["lifecycle"]["status"] == "cancelled",
        first_delivered=len(first["consumed"]) == 1,
        chunk_partial=0 < len(chunk["consumed"]) < CHUNK_ACTIONS,
        worker_tokens_equal=all(
            [t for r in call["consumed"] for t in r["tokens"]]
            == expected[:len(call["consumed"]) * ACTION_CHANNELS] for call in calls
        ),
        consumed_fresh=all(
            r["observed_ns"] <= r["ready_ns"] <= r["consumed_ns"] < r["expires_ns"]
            for call in calls for r in call["consumed"]
        ),
        control_responsive=all(
            call["max_tick_gap_s"] <= config["max_tick_gap_s"]
            for call in (*calls, result["worker"]["startup"])
        ),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("package", "image", "out", "config"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    save(args.out / "config.json", config)
    timer = threading.Timer(config["watchdog_s"], lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    result = dict(scope="saved-frame inference and control-tick surrogate; no flight", passed=False)
    try:
        result["model"] = model_probe(args, config)
        save(args.out / "result.json", result)
        result["worker"] = worker_probe(args, config)
        result["worker_checks"] = worker_checks(result, config)
        result["passed"] = all(all(p["checks"].values()) for p in result["model"]["pairs"])
        result["passed"] &= result["model"]["base_text_equal"]
        result["passed"] &= result["model"]["tensor_versions_unchanged"]
        result["passed"] &= result["model"]["all_frozen"]
        result["passed"] &= all(result["worker_checks"].values())
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        save(args.out / "result.json", result)
        timer.cancel()
    return int(not result["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
