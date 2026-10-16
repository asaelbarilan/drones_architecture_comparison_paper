import pytest

from uavlab.plugins.inference.qwen_cache import ByteLRU, Prefix, QwenReuse
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


def prefix(tokens, images=(), positions=None):
    return Prefix(
        tuple(tokens), tuple(positions or [(i, i, i) for i in range(len(tokens))]), images
    )


def test_exact_prefix_stops_at_text_change_and_never_reuses_generated_answer():
    old = prefix([1, 2, 3, 4, 5])
    assert old.common(prefix([1, 2, 3, 9, 5]), 10) == 3
    assert old.common(prefix([1, 2, 3, 4, 5, 6]), 4) == 4


def test_same_placeholder_tokens_do_not_mean_same_image():
    old = prefix([1, 2, 8, 8, 3], ((2, 4, "image-a"),))
    new = prefix([1, 2, 8, 8, 3], ((2, 4, "image-b"),))
    assert old.common(new, 5) == 2
    assert old.common(old, 5) == 5


def test_stable_keyframe_survives_latest_image_change_and_order_does_not():
    ids = [1, 8, 8, 2, 8, 8, 3]
    a = prefix(ids, ((1, 3, "first"), (4, 6, "latest-a")))
    b = prefix(ids, ((1, 3, "first"), (4, 6, "latest-b")))
    c = prefix(ids, ((1, 3, "latest-a"), (4, 6, "first")))
    assert a.common(b, 7) == 4
    assert a.common(c, 7) == 1


def test_multimodal_position_change_invalidates_prefix():
    a = prefix([1, 2, 3])
    b = prefix([1, 2, 3], positions=[(0, 0, 0), (1, 2, 1), (2, 2, 2)])
    assert a.common(b, 3) == 1


def test_lru_is_byte_bounded_and_counts_replacements_eviction_and_clear():
    cache = ByteLRU(10, 2)
    assert cache.put("a", "one", 6)
    assert cache.put("b", "two", 4)
    assert cache.get("a") == "one"
    assert cache.put("c", "three", 4)
    assert cache.get("b") is None
    assert cache.bytes == 10 and cache.evictions == 1
    assert cache.put("a", "small", 1)
    assert cache.bytes == 5
    assert not cache.put("huge", "reject", 11)
    assert cache.pop("c") == "three" and cache.bytes == 1
    cache.clear()
    assert cache.bytes == 0 and not cache.entries


def test_cache_keys_separate_role_and_weight_mode():
    cache = ByteLRU(10, 4)
    cache.put((123, "base", "monitor"), "monitor history", 2)
    cache.put((123, "base", "direction"), "direction history", 2)
    assert cache.get((123, "pilot", "pilot")) is None
    assert cache.get((124, "base", "monitor")) is None
    assert cache.pop((123, "base", "direction")) == "direction history"
    assert cache.get((123, "base", "monitor")) == "monitor history"


def test_reset_and_close_release_all_cached_state():
    backend = SharedQwenInference("unused", cache_reuse=True)
    for method in (lambda: backend.reset(None, 0), backend.close):
        backend.reuse.kv.put("key", "prefix", 10)
        backend.reuse.vision.put("key", "features", 10)
        method()
        assert backend.reuse.kv.bytes == backend.reuse.vision.bytes == 0


def test_feature_exceptions_clear_entries_at_backend_boundary():
    import asyncio

    from uavlab.interfaces import InferenceRequest

    backend = SharedQwenInference("unused", cache_reuse=True)
    backend.reuse.kv.put("key", "prefix", 10)

    def fail(_):
        raise RuntimeError("cancelled generation")

    backend._run = fail
    with pytest.raises(RuntimeError, match="cancelled"):
        asyncio.run(
            backend.invoke(
                InferenceRequest(
                    model_id=backend.model_id,
                    role="monitor",
                    prompt_hash="fixture",
                )
            )
        )
    assert backend.reuse.kv.bytes == 0


def test_invalid_limits_and_role_modes_fail_before_touching_model():
    with pytest.raises(ValueError):
        QwenReuse(max_tokens=0)
    with pytest.raises(ValueError):
        ByteLRU(-1, 1)


def test_cached_profile_opt_in_keeps_original_profile_unchanged():
    from uavlab.core.compose import load_architecture

    original = load_architecture("shared_qwen_vla_dev")
    candidate = load_architecture("shared_qwen_vla_cached_dev")
    assert not original.inference.params.get("cache_reuse", False)
    assert candidate.inference.params["cache_reuse"]
    assert candidate.scheduler == original.scheduler
