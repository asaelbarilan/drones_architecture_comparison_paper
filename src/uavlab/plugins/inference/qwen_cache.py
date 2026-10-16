"""Bounded, adapter-aware inference caches for the Qwen3-VL development backend.

No torch import at module scope. A KV entry belongs to one role and weight mode.
It contains an exact prompt prefill, never a previous generated answer.
Partial-prefix reuse is deliberately excluded: the local NF4 implementation
changed outputs when recomputing a shorter suffix. A changed input uses fresh
decoder prefill. Qwen recomputes multimodal positions on every new request.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass


class ByteLRU:
    def __init__(self, max_bytes, max_entries):
        if max_bytes < 0 or max_entries < 0:
            raise ValueError("cache limits must be nonnegative")
        self.max_bytes, self.max_entries = int(max_bytes), int(max_entries)
        self.entries = OrderedDict()
        self.bytes = 0
        self.evictions = 0

    def pop(self, key):
        item = self.entries.pop(key, None)
        if item is None:
            return None
        self.bytes -= item[1]
        return item[0]

    def get(self, key):
        item = self.entries.get(key)
        if item is None:
            return None
        self.entries.move_to_end(key)
        return item[0]

    def put(self, key, value, size):
        self.pop(key)
        if size < 0:
            raise ValueError("negative cache size")
        if size > self.max_bytes or self.max_entries == 0:
            return False
        while self.entries and (
            self.bytes + size > self.max_bytes or len(self.entries) >= self.max_entries
        ):
            _, (_, old_size) = self.entries.popitem(last=False)
            self.bytes -= old_size
            self.evictions += 1
        self.entries[key] = (value, int(size))
        self.bytes += size
        return True

    def clear(self):
        self.entries.clear()
        self.bytes = 0


@dataclass(frozen=True)
class Prefix:
    tokens: tuple
    positions: tuple
    # (first image token, exclusive last image token, processed image/grid digest)
    images: tuple = ()

    def common(self, other, limit):
        count = 0
        for a, b, pa, pb in zip(
            self.tokens, other.tokens, self.positions, other.positions, strict=False
        ):
            if count >= limit or a != b or pa != pb:
                break
            count += 1
        old = {(start, end): digest for start, end, digest in self.images}
        new = {(start, end): digest for start, end, digest in other.images}
        for span in old.keys() | new.keys():
            if span[0] < count and old.get(span) != new.get(span):
                count = min(count, span[0])
        return count


def tensor_digest(tensor):
    import torch

    value = tensor.detach().cpu().contiguous()
    digest = hashlib.sha256()
    digest.update(str((tuple(value.shape), str(value.dtype))).encode())
    digest.update(value.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def tensor_bytes(value):
    if isinstance(value, tuple | list):
        return sum(tensor_bytes(x) for x in value)
    return value.numel() * value.element_size()


class QwenReuse:
    """One owner, single-sequence greedy generation; no concurrent model calls.

    Uses a scoped wrapper at Qwen's decoder boundary. Existing generation, logits
    processors, full attention masks, visual features, and RoPE indexing stay
    native. Images are memoized as an exact ordered batch, not approximate hits.
    Retained-byte limits exclude the ordinary current-request generation cache.
    """

    def __init__(self, kv_bytes=256 * 1024**2, vision_bytes=64 * 1024**2, max_tokens=1024):
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive")
        self.kv = ByteLRU(kv_bytes, 4)
        self.vision = ByteLRU(vision_bytes, 8)
        self.max_tokens = int(max_tokens)
        self.last = {}
        self._active = False

    def clear(self):
        self.kv.clear()
        self.vision.clear()
        self.last = {}

    @staticmethod
    def _images(batch, tokens, config):
        pixels, grids = batch.get("pixel_values"), batch.get("image_grid_thw")
        if pixels is None:
            if config.image_token_id in tokens:
                raise ValueError("image placeholders without pixels")
            return (), None
        offset, cursor = 0, 0
        images = []
        merge = config.vision_config.spatial_merge_size**2
        for grid in grids:
            patches = int(grid.prod().item())
            count = patches // merge
            start = tokens.index(config.image_token_id, cursor)
            if tuple(tokens[start : start + count]) != (config.image_token_id,) * count:
                raise ValueError("image placeholder/grid mismatch")
            digest = (tensor_digest(pixels[offset : offset + patches]), tensor_digest(grid))
            images.append((start, start + count, digest))
            offset, cursor = offset + patches, start + count
        if offset != pixels.shape[0] or sum(b - a for a, b, _ in images) != tokens.count(
            config.image_token_id
        ):
            raise ValueError("image batch length mismatch")
        return tuple(images), tuple(x[2] for x in images)

    def generate(self, model, batch, role, weight_mode, **generation):
        import torch
        import transformers
        from transformers.modeling_outputs import BaseModelOutputWithPast

        if transformers.__version__ != "4.57.3":
            raise RuntimeError("Qwen cache boundary is validated with Transformers 4.57.3 only")
        if self._active:
            raise RuntimeError("cache owner cannot generate concurrently")
        base = model.get_base_model() if hasattr(model, "get_base_model") else model
        if base.config.model_type != "qwen3_vl":
            raise ValueError("cache backend supports Qwen3-VL only")
        if role not in {"planner", "direction", "monitor", "pilot"}:
            raise ValueError("unknown cache role")
        expected = "pilot" if role == "pilot" else "base"
        if weight_mode != expected:
            raise ValueError("role/weight-mode mismatch")
        if generation.get("do_sample", False) or generation.get("num_beams", 1) != 1:
            raise ValueError("cache backend requires single-sequence greedy generation")
        if not generation.get("use_cache", True):
            raise ValueError("persistent reuse requires use_cache=True")
        if batch["input_ids"].shape[0] != 1 or "pixel_values_videos" in batch:
            raise ValueError("cache backend supports one image/text sequence, no video")
        mask = batch.get("attention_mask")
        if mask is not None and (mask.ndim != 2 or not bool(mask.eq(1).all())):
            raise ValueError("cache backend requires an unpadded sequence")
        tokens = tuple(batch["input_ids"][0].tolist())
        images, image_key = self._images(batch, tokens, base.config)
        # Instance/precision changes cannot reuse entries from another loaded base.
        namespace = (id(base), weight_mode)
        key = (*namespace, role)
        previous = self.kv.pop(key)  # exclusive ownership of mutable DynamicCache
        core = base.model
        decoder = core.language_model
        original_features = core.get_image_features
        original_forward = decoder.forward
        had_override = "get_image_features" in core.__dict__
        had_forward = "forward" in decoder.__dict__
        captured = {}
        self.last = dict(role=role, mode=weight_mode, reused_tokens=0, vision_hit=False)
        self._active = True

        def features(pixel_values, image_grid_thw):
            feature_key = (*namespace, image_key, str(pixel_values.device), str(core.visual.dtype))
            value = self.vision.get(feature_key)
            if value is None:
                value = original_features(pixel_values, image_grid_thw)
                self.vision.put(feature_key, value, tensor_bytes(value))
            else:
                self.last["vision_hit"] = True
            return value

        def forward(*args, **kwargs):
            if captured:
                return original_forward(*args, **kwargs)
            if args or kwargs["inputs_embeds"].shape[1] != len(tokens):
                raise RuntimeError("unexpected Qwen prefill signature")
            # Qwen computed these from this full request, including new image grids.
            positions = tuple(map(tuple, kwargs["position_ids"][:, 0].T.tolist()))
            prefix = Prefix(tokens, positions, images)
            captured["prefix"] = prefix
            self.last["input_tokens"] = len(tokens)
            self.last["matching_prefix_tokens"] = (
                previous[0].common(prefix, len(tokens)) if previous else 0
            )
            if previous is not None and previous[0] == prefix:
                _, cache, hidden = previous
                if cache.get_seq_length() != len(tokens):
                    raise RuntimeError("corrupt prefill cache length")
                self.last["reused_tokens"] = len(tokens)
                self.last["kv_status"] = "exact_prefill_hit"
                output = BaseModelOutputWithPast(last_hidden_state=hidden, past_key_values=cache)
            else:
                self.last["kv_status"] = "changed_input" if previous else "cold"
                output = original_forward(*args, **kwargs)
            captured["cache"] = output.past_key_values
            captured["hidden"] = output.last_hidden_state[:, -1:].detach().clone()
            return output

        decoder.forward = forward
        core.get_image_features = features
        try:
            output = model.generate(**batch, **generation)
            cache = captured.get("cache")
            if cache is not None and len(tokens) <= self.max_tokens:
                # Store only prefill, discard all generated-answer KV. Compact
                # tensors so a slice cannot retain unaccounted full storage.
                length = len(tokens)
                size = sum(
                    tensor_bytes((x.keys, x.values)) // x.keys.shape[-2] * length
                    for x in cache.layers
                ) + tensor_bytes(captured["hidden"])
                if size <= self.kv.max_bytes:
                    cache.crop(len(tokens))
                    for layer in cache.layers:
                        layer.keys = layer.keys.clone(memory_format=torch.contiguous_format)
                        layer.values = layer.values.clone(memory_format=torch.contiguous_format)
                    self.kv.put(key, (captured["prefix"], cache, captured["hidden"]), size)
            self.last.update(kv_bytes=self.kv.bytes, vision_bytes=self.vision.bytes)
            return output
        except BaseException:
            # No partially extended cache survives an error or cancellation.
            self.clear()
            raise
        finally:
            if had_forward:
                decoder.forward = original_forward
            else:
                del decoder.forward
            if had_override:
                core.get_image_features = original_features
            else:
                del core.get_image_features
            self._active = False
