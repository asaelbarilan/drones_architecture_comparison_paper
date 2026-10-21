"""D207 input validation and action codec boundary; no model ownership."""

from __future__ import annotations

import base64
import io
import json

# The frozen UAV-Flow checkpoint predicts eight actions with four channels each.
ACTION_CHANNELS = 4
CHUNK_ACTIONS = 8
BOX_SCALE = 1000  # Trained bounding-box coordinates are normalized to [0, 1000].


def read_pilot(request):
    import numpy as np

    if len(request.images) != 1:
        raise ValueError("pilot requires one current image")
    data = json.loads(request.prompt)
    if set(data) != {"instruction", "state", "remaining", "box"}:
        raise ValueError("pilot requires explicit instruction/state/remaining/box")
    for key in ("state", "remaining"):
        value = data[key]
        if not isinstance(value, list) or len(value) != ACTION_CHANNELS:
            raise ValueError(f"invalid pilot {key}")
        if not np.isfinite(value).all():
            raise ValueError(f"invalid pilot {key}")
    box = data["box"]
    if box is not None and (
        len(box) != ACTION_CHANNELS or not all(0 <= v <= BOX_SCALE for v in box)
    ):
        raise ValueError("invalid normalized box")
    return data


def encode_pilot(backend, request, data):
    from PIL import Image

    state = ",".join(str(round(float(x), 1)) for x in data["state"])
    row = dict(
        prompt=backend.codec.OFFICIAL_PROMPT.format(state=state, instruction=data["instruction"]),
        progress_text=backend.codec.progress_text(data["remaining"]),
        box_text=json.dumps({"bbox_2d": data["box"] or []}) + "\n",
    )
    image = Image.open(io.BytesIO(base64.b64decode(request.images[0]))).convert("RGB")
    return backend.codec.encode(
        backend.processor, backend.tokenizer, row, CHUNK_ACTIONS, with_answer=False, image=image
    )


def action_logits(tokenizer):
    import torch
    from transformers import LogitsProcessor, LogitsProcessorList

    low, high = tokenizer.vocab_size - tokenizer.n_bins, tokenizer.vocab_size

    class ActionOnly(LogitsProcessor):
        def __call__(self, input_ids, scores):
            masked = torch.full_like(scores, float("-inf"))
            masked[:, low:high] = scores[:, low:high]
            return masked

    return LogitsProcessorList([ActionOnly()])


def decode_actions(tokenizer, ids, count):
    import numpy as np

    steps = tokenizer.decode(ids, count)
    if steps is None or np.asarray(steps).shape != (count, ACTION_CHANNELS):
        raise ValueError("invalid decoded VLA action chunk")
    if not np.isfinite(steps).all():
        raise ValueError("invalid decoded VLA action chunk")
    return np.asarray(steps).tolist()


BOX_PREFIX = '{"bbox_2d": ['
BOX_TOKENS = 52  # box + optional next box line, as the packaged UAV-Flow server
LINE_TOKENS = 32  # one "Left +FF.F,+SS.S,+UU.U,+YYY" progress line


def read_line_request(request):
    """D-162 native VLA line: the D207 adapter's own box and progress line (no goal given)."""
    if len(request.images) != 1:
        raise ValueError("VLA line requires one current image")
    data = json.loads(request.prompt)
    if set(data) != {"instruction", "state"} or len(data["state"]) != ACTION_CHANNELS:
        raise ValueError("VLA line requires instruction and four-channel state")
    return data


def native_line(backend, request):
    """Phase 0 + 1 of the packaged server (--box --progress): greedy box line, then the
    progress line conditioned on it. Returns the parsed box and Left line as JSON text."""
    from PIL import Image

    data, codec = read_line_request(request), backend.codec
    image = Image.open(io.BytesIO(base64.b64decode(request.images[0]))).convert("RGB")
    state = ",".join(str(round(float(x), 1)) for x in data["state"])
    row = dict(prompt=codec.OFFICIAL_PROMPT.format(state=state, instruction=data["instruction"]))
    prefix = backend.processor.tokenizer.encode(BOX_PREFIX, add_special_tokens=False)
    encoded = codec.encode(backend.processor, backend.tokenizer, row, CHUNK_ACTIONS,
                           with_answer=False, image=image)
    box_ids = greedy(backend, request, codec.append_ids(encoded, prefix), BOX_TOKENS)
    text = BOX_PREFIX + backend.processor.tokenizer.decode(box_ids, skip_special_tokens=True)
    box = codec.parse_box(text.split("Left")[0])
    row["box_text"] = codec.box_text(box or [])
    batch = codec.encode(backend.processor, backend.tokenizer, row, CHUNK_ACTIONS,
                         with_answer=False, image=image)
    line_ids = greedy(backend, request, batch, LINE_TOKENS)
    said = backend.processor.tokenizer.decode(line_ids, skip_special_tokens=True)
    left = codec.parse_progress(said)
    payload = dict(box=box, left=None if left is None else [float(v) for v in left], said=said)
    return json.dumps(payload), len(box_ids) + len(line_ids)


def greedy(backend, request, batch, tokens):
    pad = backend.processor.tokenizer.pad_token_id
    output = backend._generate(request, batch, do_sample=False, max_new_tokens=tokens,
                               use_cache=True, pad_token_id=pad)
    return output[0, batch["input_ids"].shape[1]:].tolist()
