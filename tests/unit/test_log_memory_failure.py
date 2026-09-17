"""Optional analysis export must not hide a completed episode on memory failure."""

import json

import pytest

from uavlab.contracts import EventType
from uavlab.core.event_log import EventLog


def test_arrow_allocation_failure_retains_primary_log_and_closes(tmp_path, monkeypatch):
    pa = pytest.importorskip("pyarrow")

    def exhausted(*args, **kwargs):
        raise pa.ArrowMemoryError("allocation failed")

    monkeypatch.setattr(pa, "array", exhausted)
    log = EventLog("oom-regression", tmp_path)
    log.emit(
        "orchestrator",
        EventType.EPISODE_END,
        31_000_000_000,
        0,
        {"reason": "runtime_error", "success": False},
    )
    with pytest.warns(RuntimeWarning, match="Parquet export skipped"):
        assert log.write_parquet() is None
    # Visible before close: loss of the optional exporter cannot hide termination.
    rows = [json.loads(x) for x in (tmp_path / "events.jsonl").read_text().splitlines()]
    assert rows[-1]["payload"]["reason"] == "runtime_error"
    log.close()
    assert log._jsonl is None
