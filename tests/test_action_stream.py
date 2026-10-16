import json
from dataclasses import replace

import numpy as np
import pytest

from uavlab.plugins.inference.action_buffer import ActionBuffer
from uavlab.plugins.inference.action_stream import (
    ActionTokenStream,
    GenerationCancelled,
    StreamOptions,
)
from uavlab.plugins.inference.qwen_actions import ACTION_CHANNELS, CHUNK_ACTIONS

# Same bin count as the frozen action codec; test values are identities, not motion.
TEST_BINS = 256


class Codec:
    def is_action_token(self, token):
        return 0 <= token < TEST_BINS

    def decode(self, tokens, count):
        return np.asarray(tokens, dtype=float).reshape(count, ACTION_CHANNELS)


def stream_fixture(count=CHUNK_ACTIONS):
    records = []
    options = StreamOptions(count, records.append, lambda: False)
    stream = ActionTokenStream(Codec(), options)
    stream.put(np.asarray([[999, 888]]))
    return stream, records


def test_prompt_is_skipped_and_actions_arrive_before_chunk_end():
    stream, records = stream_fixture()
    ids = list(range(CHUNK_ACTIONS * ACTION_CHANNELS))
    for index, token in enumerate(ids):
        stream.put(np.asarray([token]))
        assert len(records) == (index + 1) // ACTION_CHANNELS
    stream.end()
    assert [t for record in records for t in record["tokens"]] == ids
    assert all(len(r["step_fru_m_yaw_rad"]) == ACTION_CHANNELS for r in records)
    json.dumps(records, allow_nan=False)


@pytest.mark.parametrize("partial", range(ACTION_CHANNELS))
def test_cancellation_never_emits_a_partial_action(partial):
    stream, records = stream_fixture()
    for token in range(partial):
        stream.put(np.asarray([token]))
    stream.options = replace(stream.options, cancelled=lambda: True)
    with pytest.raises(GenerationCancelled):
        stream.put(np.asarray([0]))
    assert not records


def test_incomplete_and_non_action_tokens_fail_closed():
    stream, records = stream_fixture()
    stream.put(np.asarray([0]))
    with pytest.raises(ValueError, match="incomplete"):
        stream.end()
    with pytest.raises(ValueError, match="non-action"):
        stream.put(np.asarray([999]))
    assert not records


def test_requested_action_count_is_bounded():
    stream, records = stream_fixture(1)
    for token in range(ACTION_CHANNELS):
        stream.put(np.asarray([token]))
    stream.end()
    with pytest.raises(ValueError, match="exceeds"):
        stream.put(np.asarray([0]))
    assert len(records) == 1
    for count in (0, CHUNK_ACTIONS + 1, True):
        with pytest.raises(ValueError):
            StreamOptions(count, records.append, lambda: False)


def packet(index=0):
    return dict(
        request_id=1, goal_version=1, observation_seq=7, index=index,
        observed_ns=10, ready_ns=20, expires_ns=100,
        tokens=[1] * ACTION_CHANNELS, step_fru_m_yaw_rad=[0.1] * ACTION_CHANNELS,
    )


def test_json_buffer_accepts_later_actions_without_waiting_for_whole_chunk():
    buffer = ActionBuffer()
    buffer.begin(1, 1)
    first, second = packet(), packet(1)
    buffer.append(json.loads(json.dumps(first)))
    assert buffer.take(1, first["ready_ns"]) == first
    assert buffer.take(1, first["ready_ns"]) is None
    buffer.append(second)
    assert buffer.take(1, second["ready_ns"]) == second


@pytest.mark.parametrize("change", ["expired", "revoked", "new_goal"])
def test_queued_action_is_rechecked_at_consumption(change):
    buffer, record = ActionBuffer(), packet()
    buffer.begin(1, 1)
    buffer.append(record)
    goal, now = record["goal_version"], record["ready_ns"]
    if change == "expired":
        now = record["expires_ns"]
    elif change == "revoked":
        buffer.revoke()
    else:
        goal += 1
    assert buffer.take(goal, now) is None
    assert not buffer.queue


def test_buffer_rejects_missing_actions_wrong_requests_partial_and_full():
    buffer = ActionBuffer(capacity=1)
    buffer.begin(1, 1)
    for field, value in (("index", 1), ("request_id", 2), ("step_fru_m_yaw_rad", [1])):
        record = packet()
        record[field] = value
        with pytest.raises(ValueError):
            buffer.append(record)
    buffer.append(packet())
    with pytest.raises(ValueError, match="full"):
        buffer.append(packet(1))


def test_code_size_checker_rejects_long_function_and_ignores_docstring():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("check_code", Path("scripts/check_code.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rules = json.loads(Path("configs/code_rules.json").read_text())
    limit = rules["max_function_lines"]
    assert module.length_violations("def f():\n" + "    pass\n" * limit, rules)
    source = 'def f():\n    """' + "doc\n" * limit + '    """\n    pass\n'
    assert not module.length_violations(source, rules)


def test_one_action_profile_is_explicit_and_original_keeps_chunk():
    from uavlab.core.compose import load_architecture
    from uavlab.plugins.inference.shared_qwen import SharedQwenInference

    old = load_architecture("shared_qwen_vla_dev")
    new = load_architecture("shared_qwen_vla_first_action_dev")
    assert "pilot_actions" not in old.inference.params
    assert new.inference.params["pilot_actions"] == 1
    assert SharedQwenInference("unused").pilot_actions == CHUNK_ACTIONS
    for invalid in (0, CHUNK_ACTIONS + 1, True):
        with pytest.raises(ValueError):
            SharedQwenInference("unused", pilot_actions=invalid)
