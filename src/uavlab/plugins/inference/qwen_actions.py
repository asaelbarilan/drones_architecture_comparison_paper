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
