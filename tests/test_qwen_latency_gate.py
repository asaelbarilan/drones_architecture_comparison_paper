import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from uavlab.live_qwen import latency, runner


def gate(monkeypatch, samples):
    pending = iter(samples)
    rows = []

    async def measured(worker, request, settings):
        return next(pending)

    monkeypatch.setattr(latency, "sample", measured)
    request = SimpleNamespace(prompt="test", images=())
    work = latency.qualify(SimpleNamespace(last_id=-1), request,
                           dict(pilot_ttl_s=1.5, control_hz=20), rows.append)
    return work, rows


def test_gate_accepts_warm_samples_after_nonexecuting_cold_expiry(monkeypatch):
    cold = dict(first_action_s=None, status="cancelled")
    warm = dict(first_action_s=0.55, status="complete")
    work, rows = gate(monkeypatch, [cold, warm, warm, warm])
    assert len(asyncio.run(work)) == latency.WARM_REPEATS+1
    assert all(not row["execution_allowed"] for row in rows)


@pytest.mark.parametrize("bad", [dict(first_action_s=None, status="cancelled"),
                                dict(first_action_s=1.46, status="complete"),
                                dict(first_action_s=0.2, status="failed")])
def test_gate_refuses_expiry_insufficient_margin_or_failure(monkeypatch, bad):
    work, _ = gate(monkeypatch, [dict(first_action_s=0.7, status="complete"), bad])
    with pytest.raises(RuntimeError, match="preflight"):
        asyncio.run(work)


def test_failed_preflight_cannot_enter_flight_loop(monkeypatch, tmp_path):
    settings = json.loads(Path("configs/experiments/qwen_async_local.json").read_text())
    called = []

    async def refuse(*args):
        raise RuntimeError("latency preflight failed")

    async def reset(*args):
        return SimpleNamespace()

    async def close():
        called.append("closed")

    async def forbidden(*args):
        called.append("flight")

    monkeypatch.setattr(runner, "qualify", refuse)
    monkeypatch.setattr(runner, "diagnostic_request", lambda *args: None)
    monkeypatch.setattr(runner, "flight_loop", forbidden)
    monkeypatch.setattr(runner, "LiveControl", lambda *args: None)
    monkeypatch.setattr(runner.REGISTRY, "build", lambda *args, **kw:
                        SimpleNamespace(reset=reset, close=close))
    worker = SimpleNamespace(last_id=-1, revoke=lambda: called.append("revoked"))
    with pytest.raises(RuntimeError, match="preflight"):
        asyncio.run(runner.fly(worker, settings["missions"][0], settings, tmp_path / "blocked"))
    assert called == ["revoked", "closed"]
    assert (tmp_path / "blocked" / "failure.json").is_file()
