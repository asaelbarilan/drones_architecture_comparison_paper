"""One spawned GPU owner; wall-clock callers poll without awaiting inference.

This boundary is deliberately separate from deterministic SimClock orchestration.
Only one request is admitted at a time; priority scheduling belongs above it.
"""

from __future__ import annotations

import multiprocessing as mp
import queue
import time
from contextlib import suppress
from dataclasses import dataclass

from uavlab.interfaces import InferenceRequest

from .action_stream import GenerationCancelled, StreamOptions
from .qwen_actions import CHUNK_ACTIONS
from .shared_qwen import SharedQwenInference

# One chunk plus lifecycle messages; IPC memory cannot grow with a stalled consumer.
RESULT_SLOTS = CHUNK_ACTIONS + 4
IPC_POLL_S = 0.05  # Cancellation polling interval for a full delivery queue.


@dataclass(frozen=True)
class WorkItem:
    request_id: int
    goal_version: int
    observed_ns: int
    expires_ns: int
    request: InferenceRequest
    actions: int = CHUNK_ACTIONS

    def __post_init__(self):
        if self.observed_ns < 0 or self.expires_ns <= self.observed_ns:
            raise ValueError("invalid observation lifetime")
        if type(self.actions) is not int or not 1 <= self.actions <= CHUNK_ACTIONS:
            raise ValueError("invalid action count")


def valid_work(item, goal_version, now_ns):
    return item.goal_version == goal_version and item.observed_ns <= now_ns < item.expires_ns


def _send(outbox, event, cancel):
    while not cancel.is_set():
        try:
            outbox.put(event, timeout=IPC_POLL_S)
            return
        except queue.Full:
            continue
    raise GenerationCancelled("delivery cancelled")


def _perform(backend, item, outbox, cancel):
    def cancelled():
        return cancel.is_set() or time.perf_counter_ns() >= item.expires_ns

    def emit(payload):
        _send(outbox, dict(kind="action", item=item, payload=payload), cancel)

    if cancelled():
        raise GenerationCancelled("expired before inference")
    if item.request.role not in backend.ROLES or item.request.model_id != backend.model_id:
        raise ValueError("unknown role or model")
    if item.request.role == "pilot":
        result = backend.stream_pilot(item.request, StreamOptions(item.actions, emit, cancelled))
    else:
        result = backend._run(item.request)
    if cancelled():
        raise GenerationCancelled("expired after inference")
    _send(outbox, dict(kind="result", item=item, payload=result), cancel)


def _job(backend, item, outbox, cancel):
    try:
        _perform(backend, item, outbox, cancel)
        status, error = "complete", None
    except GenerationCancelled as exc:
        status, error = "cancelled", str(exc)
    except Exception as exc:
        backend.clear_caches()
        status, error = "failed", f"{type(exc).__name__}: {exc}"
    # Space is reserved for lifecycle messages by the single-request contract.
    outbox.put(dict(kind="done", item=item, payload=dict(status=status, error=error)))


def _worker_main(factory, settings, channels):
    inbox, outbox, cancel = channels
    backend = factory(**settings)
    try:
        backend._load()
        outbox.put(dict(kind="ready", payload=dict(load_count=backend.load_count)))
        while True:
            item = inbox.get()
            if item is None:
                break
            _job(backend, item, outbox, cancel)
    except Exception as exc:
        outbox.put(dict(kind="fatal", payload=f"{type(exc).__name__}: {exc}"))
    finally:
        backend.close()


class QwenWorker:
    def __init__(self, settings, factory=SharedQwenInference):
        context = mp.get_context("spawn")
        self.inbox = context.Queue(maxsize=1)
        self.outbox = context.Queue(maxsize=RESULT_SLOTS)
        self.cancel = context.Event()
        self.process = context.Process(
            target=_worker_main, args=(factory, settings, (self.inbox, self.outbox, self.cancel)),
            daemon=True,
        )
        self.current = None
        self.ready = False
        self.last_id = -1

    def start(self):
        self.process.start()

    def submit(self, item):
        if not self.ready or self.current is not None:
            raise RuntimeError("worker is not ready or already busy")
        if item.request_id <= self.last_id:
            raise ValueError("request IDs must increase")
        if not valid_work(item, item.goal_version, time.perf_counter_ns()):
            raise ValueError("request observation is expired or in the future")
        self.cancel.clear()
        self.inbox.put_nowait(item)
        self.current, self.last_id = item, item.request_id

    def revoke(self):
        self.cancel.set()

    def poll(self, goal_version, now_ns=None):
        now_ns = time.perf_counter_ns() if now_ns is None else now_ns
        events = []
        while True:
            try:
                event = self.outbox.get_nowait()
            except queue.Empty:
                break
            events.append(self._receive(event, goal_version, now_ns))
        if not self.process.is_alive() and not any(e["kind"] == "fatal" for e in events):
            raise RuntimeError("inference worker exited")
        return events

    def _receive(self, event, goal_version, now_ns):
        kind, item = event["kind"], event.get("item")
        if kind == "ready":
            self.ready = True
        elif kind == "done" and self.current == item:
            self.current = None
        elif kind in {"action", "result"}:
            accepted = self.current == item and not self.cancel.is_set()
            if not accepted or not valid_work(item, goal_version, now_ns):
                return dict(kind="discarded", item=item, payload=dict(original_kind=kind))
        return event

    def close(self, timeout_s=5.0):
        self.revoke()
        with suppress(queue.Full):
            self.inbox.put_nowait(None)
        if self.process.pid is not None:
            self.process.join(timeout_s)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout_s)
        for channel in (self.inbox, self.outbox):
            channel.cancel_join_thread()
            channel.close()
