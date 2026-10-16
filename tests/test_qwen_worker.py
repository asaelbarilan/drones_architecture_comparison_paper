import os
import time

import pytest

from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.action_stream import GenerationCancelled
from uavlab.plugins.inference.qwen_actions import ACTION_CHANNELS
from uavlab.plugins.inference.qwen_worker import QwenWorker, WorkItem

# Test-only injected latency, independent of the real model's measured latency.
DELAY_S = 0.08
POLL_S = 0.005
TEST_TIMEOUT_S = 8.0
NS_PER_SECOND = 1_000_000_000


class SlowBackend:
    ROLES = frozenset({"pilot", "monitor"})
    model_id = "test"
    load_count = 1

    def _load(self):
        pass

    def close(self):
        pass

    def clear_caches(self):
        pass

    def stream_pilot(self, request, delivery):
        for index in range(delivery.actions):
            time.sleep(DELAY_S)
            if delivery.cancelled():
                raise GenerationCancelled("cancelled in fake decode")
            delivery.emit(dict(index=index, tokens=[1] * ACTION_CHANNELS, pid=os.getpid()))
        return "done", delivery.actions * ACTION_CHANNELS

    def _run(self, request):
        raise ValueError("deliberate worker failure")


def pump(worker, finished):
    end = time.perf_counter() + TEST_TIMEOUT_S
    records, ticks = [], 0
    while time.perf_counter() < end:
        records.extend(worker.poll(1))
        ticks += 1
        if finished():
            return records, ticks
        time.sleep(POLL_S)
    raise AssertionError("worker did not finish within test deadline")


@pytest.fixture
def worker():
    value = QwenWorker({}, SlowBackend)
    value.start()
    try:
        pump(value, lambda: value.ready)
        yield value
    finally:
        value.close()
    assert not value.process.is_alive()


def item(role="pilot"):
    now = time.perf_counter_ns()
    return WorkItem(
        request_id=1, goal_version=1, observed_ns=now,
        expires_ns=now + int(TEST_TIMEOUT_S * NS_PER_SECOND),
        request=InferenceRequest(model_id="test", role=role, prompt_hash="test"), actions=2,
    )


def test_control_polls_continue_while_separate_process_streams(worker):
    worker.submit(item())
    records, ticks = pump(worker, lambda: worker.current is None)
    actions = [r for r in records if r["kind"] == "action"]
    assert len(actions) == item().actions
    assert all(r["payload"]["pid"] != os.getpid() for r in actions)
    assert ticks > DELAY_S / POLL_S
    assert records[0]["kind"] == "action"
    assert records[-1]["payload"]["status"] == "complete"


def test_busy_worker_cannot_duplicate_job(worker):
    worker.submit(item())
    with pytest.raises(RuntimeError, match="busy"):
        worker.submit(item())
    pump(worker, lambda: worker.current is None)
    with pytest.raises(ValueError, match="increase"):
        worker.submit(item())


def test_revocation_suppresses_inflight_and_already_queued_actions(worker):
    worker.submit(item())
    time.sleep(DELAY_S * 1.5)
    worker.revoke()
    records, _ = pump(worker, lambda: worker.current is None)
    assert not any(r["kind"] == "action" for r in records)
    assert records[-1]["payload"]["status"] == "cancelled"


def test_observation_expiry_at_receive_and_new_goal_are_rejected(worker):
    work = item()
    worker.current = work
    event = dict(kind="action", item=work, payload="must not execute")
    assert worker._receive(event, 1, work.expires_ns)["kind"] == "discarded"
    assert worker._receive(event, work.goal_version + 1, work.observed_ns)["kind"] == "discarded"
    worker.current = None


def test_worker_error_is_explicit_not_a_successful_empty_action(worker):
    worker.submit(item("monitor"))
    records, _ = pump(worker, lambda: worker.current is None)
    assert not any(r["kind"] in {"action", "result"} for r in records)
    assert records[-1]["payload"]["status"] == "failed"
    assert "deliberate worker failure" in records[-1]["payload"]["error"]


def test_dead_worker_is_detected_without_waiting_for_inference(worker):
    worker.process.terminate()
    worker.process.join(TEST_TIMEOUT_S)
    with pytest.raises(RuntimeError, match="exited"):
        worker.poll(1)
