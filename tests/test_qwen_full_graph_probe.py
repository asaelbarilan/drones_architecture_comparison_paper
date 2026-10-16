"""Fresh graph buffers and role restoration for the isolated D142 prototype."""

import importlib
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest


@pytest.fixture
def probe(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "scripts/diagnostics"))
    return importlib.import_module("probe_qwen_fast_worker")


def test_graph_buffers_receive_changed_image_and_context(probe):
    torch = pytest.importorskip("torch")
    module = importlib.import_module("probe_qwen_decoder_graph")
    source = [torch.tensor([1., 2.]), torch.tensor([3.])]
    buffers = module.clone_tree(source, torch)
    module.copy_tree(buffers, [torch.tensor([4., 5.]), torch.tensor([6.])], torch)
    assert buffers[0].tolist() == [4., 5.]
    assert buffers[1].tolist() == [6.]
    assert source[0].tolist() == [1., 2.]


def test_graph_shape_change_is_rejected(probe):
    torch = pytest.importorskip("torch")
    module = importlib.import_module("probe_qwen_decoder_graph")
    with pytest.raises(ValueError, match="shape changed"):
        module.copy_tree(torch.zeros(2), torch.zeros(3), torch)


def test_pilot_exception_restores_every_role_method(probe, monkeypatch):
    backend = object.__new__(probe.ExperimentalBackend)
    backend.enabled, backend.norms = True, []
    original_decoder, original_visual, original_head = Mock(), Mock(), Mock()
    backend.decoder = SimpleNamespace(forward=original_decoder)
    backend.visual = SimpleNamespace(forward=original_visual)
    backend.head = SimpleNamespace(forward=original_head)
    backend.head_original = original_head
    backend.full_graph = SimpleNamespace(original=original_decoder, head_forward=Mock())
    backend.vision_graph = SimpleNamespace(original=original_visual)
    backend.bursts = SimpleNamespace(generate=Mock(side_effect=RuntimeError("cancelled")))
    monkeypatch.setattr(probe, "variant", lambda *args: nullcontext())
    with pytest.raises(RuntimeError, match="cancelled"):
        backend._generate(SimpleNamespace(role="pilot"), {})
    assert backend.decoder.forward is original_decoder
    assert backend.visual.forward is original_visual
    assert backend.head.forward is original_head


def test_base_role_uses_original_generation(probe, monkeypatch):
    backend = object.__new__(probe.ExperimentalBackend)
    backend.enabled = True
    original = Mock(return_value="base output")
    monkeypatch.setattr(probe.SharedQwenInference, "_generate", original)
    request = SimpleNamespace(role="monitor")
    assert backend._generate(request, {}) == "base output"
    original.assert_called_once_with(request, {})
