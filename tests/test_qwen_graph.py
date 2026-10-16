"""Graph isolation and eager fallbacks without a GPU."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from uavlab.plugins.inference.qwen_graph import GraphedMLP, PilotGraphs


def test_prefill_stays_eager():
    original = Mock(return_value="fresh")
    graph = GraphedMLP(original, None)
    value = SimpleNamespace(shape=(1, 12, 256))
    assert graph(value) == "fresh"
    original.assert_called_once_with(value)
    assert graph.graph is None


def test_changed_shape_stays_eager():
    original = Mock(return_value="fallback")
    graph = GraphedMLP(original, None)
    graph.graph = Mock()
    graph.buffer = SimpleNamespace(shape=(1, 1, 256), dtype="bf16")
    assert graph(SimpleNamespace(shape=(2, 1, 256), dtype="bf16")) == "fallback"
    graph.graph.replay.assert_not_called()


def test_scope_restores_base_roles_after_error():
    module = SimpleNamespace(forward=Mock())
    original = module.forward
    backend = fake_backend("model.language_model.layers.0.self_attn.q_proj", module)
    graphs = PilotGraphs(backend)
    with pytest.raises(RuntimeError), graphs.active():
        assert module.forward is graphs.wrappers[0]
        raise RuntimeError("cancelled")
    assert module.forward is original


def test_vision_is_excluded():
    module = SimpleNamespace(forward=Mock())
    backend = fake_backend("model.visual.blocks.0.attn.q_proj", module)
    assert not PilotGraphs(backend).modules


def fake_backend(name, module):
    embeddings = SimpleNamespace(weight=SimpleNamespace(dtype="bf16"))
    return SimpleNamespace(torch=None, model=SimpleNamespace(
        named_modules=lambda: [(name, module)], get_input_embeddings=lambda: embeddings))
