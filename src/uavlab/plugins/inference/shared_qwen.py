"""One unmerged Qwen base, four serialized roles, one optional VLA adapter.

Heavy imports are lazy. KV/image features are never reused across adapter modes.
This is a development integration, not the historical Ollama comparison profile.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path

from uavlab.core.registry import register
from uavlab.interfaces import InferenceRequest, InferenceResult


@register("inference", "shared_qwen_vla")
class SharedQwenInference:
    ROLES = frozenset({"planner", "direction", "monitor", "pilot"})

    def __init__(
        self,
        package_path: str,
        precision="nf4",
        max_new_tokens=192,
        model_id="qwen3-vl-4b-d207-shared",
        audit_path=None,
        cache_reuse=False,
        kv_cache_mib=256,
        vision_cache_mib=64,
        cache_max_tokens=1024,
        **_,
    ):
        self.package = Path(package_path)
        self.precision = precision
        self.model_id = model_id
        self.max_new_tokens = int(max_new_tokens)
        self.audit_path = Path(audit_path) if audit_path else None
        self._lock = asyncio.Lock()
        self.model = None
        self.load_count = 0
        self._services = None
        self._calls = []
        self.reuse = None
        if cache_reuse:
            from .qwen_cache import QwenReuse

            self.reuse = QwenReuse(
                kv_bytes=int(kv_cache_mib * 1024**2),
                vision_bytes=int(vision_cache_mib * 1024**2),
                max_tokens=cache_max_tokens,
            )

    @property
    def name(self):
        return "shared_qwen_vla"

    def bind_runtime(self, services):
        self._services = services

    def reset(self, mission, seed):
        self._calls.clear()
        self.clear_caches()

    def clear_caches(self):
        if self.reuse is not None:
            self.reuse.clear()

    def available(self):
        return all(
            (self.package / p).is_file()
            for p in (
                "base/config.json",
                "adapter/adapter_model.safetensors",
                "package_manifest.json",
            )
        )

    def _load(self):
        if self.model is not None:
            return
        if not self.available():
            raise FileNotFoundError(f"Complete VLA package missing: {self.package}")
        if self.precision not in {"nf4", "bf16"}:
            raise ValueError("precision must be nf4 or bf16")
        # The installed package supplies the exact trained action codec/normalization.
        scripts = self.package / "code/scripts"
        for name in ("qwen_backend", "train_uav_flow_vla", "uav_flow_action_tokenizer"):
            existing = sys.modules.get(name)
            if existing and Path(existing.__file__).parent.resolve() != scripts.resolve():
                raise RuntimeError(f"Conflicting imported VLA module: {name}")
        sys.path.insert(0, str(scripts))
        os.environ.update(
            QWEN_MODEL=str(self.package / "base"),
            UAV_FLOW_OFFICIAL_REPORT=str(self.package / "code/reports/uav_flow_official_10shard"),
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
        )
        import torch
        import train_uav_flow_vla as codec
        from peft import PeftModel
        from uav_flow_action_tokenizer import ActionTokenizer

        self.torch, self.codec = torch, codec
        self.api, self.processor, base, _ = codec.setup("qwen", self.precision)
        self.base_object_id = id(base)
        self.model = PeftModel.from_pretrained(base, str(self.package / "adapter"))
        self.model.eval()
        self.model.requires_grad_(False)
        self.model.gradient_checkpointing_disable()
        self.tokenizer = ActionTokenizer(self.processor.tokenizer, codec.official_stats())
        self.load_count += 1

    def _chat_batch(self, request):
        from PIL import Image

        images = [
            Image.open(io.BytesIO(base64.b64decode(x))).convert("RGB") for x in request.images
        ]
        content = [{"type": "image", "image": image} for image in images]
        content.append({"type": "text", "text": request.prompt})
        text = self.processor.apply_chat_template(
            [{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True
        )
        kwargs = {"images": images} if images else {}
        return self.processor(text=[text], return_tensors="pt", **kwargs)

    def _pilot(self, request):
        import numpy as np
        from PIL import Image
        from transformers import LogitsProcessor, LogitsProcessorList

        if len(request.images) != 1:
            raise ValueError("pilot requires one current image")
        data = json.loads(request.prompt)
        if set(data) != {"instruction", "state", "remaining", "box"}:
            raise ValueError("pilot requires explicit instruction/state/remaining/box")
        for key in ("state", "remaining"):
            value = data[key]
            if not isinstance(value, list) or len(value) != 4 or not np.isfinite(value).all():
                raise ValueError(f"invalid pilot {key}")
        box = data["box"]
        if box is not None and (len(box) != 4 or not all(0 <= v <= 1000 for v in box)):
            raise ValueError("invalid normalized box")
        state = ",".join(str(round(float(x), 1)) for x in data["state"])
        row = dict(
            prompt=self.codec.OFFICIAL_PROMPT.format(state=state, instruction=data["instruction"]),
            progress_text=self.codec.progress_text(data["remaining"]),
            box_text=json.dumps({"bbox_2d": box or []}) + "\n",
        )
        image = Image.open(io.BytesIO(base64.b64decode(request.images[0]))).convert("RGB")
        batch = self.codec.encode(
            self.processor, self.tokenizer, row, 8, with_answer=False, image=image
        )
        low, high = self.tokenizer.vocab_size - self.tokenizer.n_bins, self.tokenizer.vocab_size
        torch = self.torch

        class ActionOnly(LogitsProcessor):
            def __call__(self, input_ids, scores):
                masked = torch.full_like(scores, float("-inf"))
                masked[:, low:high] = scores[:, low:high]
                return masked

        output = self._generate(
            request,
            batch,
            do_sample=False,
            min_new_tokens=32,
            max_new_tokens=32,
            logits_processor=LogitsProcessorList([ActionOnly()]),
            use_cache=True,
            pad_token_id=self.processor.tokenizer.pad_token_id,
        )
        ids = output[0, batch["input_ids"].shape[1] :].tolist()
        steps = self.tokenizer.decode(ids, 8)
        if steps is None or np.asarray(steps).shape != (8, 4) or not np.isfinite(steps).all():
            raise ValueError("invalid decoded VLA action chunk")
        return {
            "steps_fru_m_yaw_rad": np.asarray(steps).tolist(),
            "tokens": ids,
            "remaining_supplied": data["remaining"],
        }, len(ids)

    def _generate(self, request, batch, **kwargs):
        batch = self.api.cuda(batch)
        if self.reuse is None:
            return self.model.generate(**batch, **kwargs)
        return self.reuse.generate(
            self.model,
            batch,
            request.role,
            "pilot" if request.role == "pilot" else "base",
            **kwargs,
        )

    def _run(self, request):
        self._load()
        mode = nullcontext() if request.role == "pilot" else self.model.disable_adapter()
        # Serialize before entering this context; no second role may switch it mid-call.
        with mode, self.torch.inference_mode():
            if request.role == "pilot":
                return self._pilot(request)
            batch = self._chat_batch(request)
            output = self._generate(
                request,
                batch,
                do_sample=False,
                max_new_tokens=self.max_new_tokens,
                use_cache=True,
                pad_token_id=self.processor.tokenizer.pad_token_id,
            )
            ids = output[0, batch["input_ids"].shape[1] :].tolist()
            return self.processor.tokenizer.decode(ids, skip_special_tokens=True), len(ids)

    async def invoke(self, request: InferenceRequest):
        if request.role not in self.ROLES or request.model_id != self.model_id:
            raise ValueError("Unknown role or mismatched shared model identity")
        async with self._lock:
            started = time.perf_counter_ns()
            # SimClock roles may park only on SimClock; an external thread await
            # would starve its pump. Match the existing synchronous Ollama backend,
            # then charge measured time. Use a process watchdog for wall-time caps.
            try:
                payload, tokens = self._run(request)
            except BaseException:
                self.clear_caches()
                raise
            elapsed = time.perf_counter_ns() - started
            record = dict(
                role=request.role,
                adapter=request.role == "pilot",
                model_id=self.model_id,
                load_count=self.load_count,
                observation_seq=request.observation_seq,
                prompt=request.prompt,
                response=payload,
                wall_latency_ns=elapsed,
                cache=dict(self.reuse.last) if self.reuse is not None else {"enabled": False},
            )
            self._calls.append(record)
            if self.audit_path:
                self.audit_path.parent.mkdir(parents=True, exist_ok=True)
                with self.audit_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(record, allow_nan=False) + "\n")
            # Real elapsed inference is charged. No cheap simulated latency claim.
            if self._services:
                await self._services.clock.sleep_ns(elapsed)
            return InferenceResult(payload=payload, output_tokens=tokens, latency_ns=elapsed)

    def stats(self):
        return {
            "inference_calls_total": float(len(self._calls)),
            "shared_base_load_count": float(self.load_count),
            "inference_latency_s_total": sum(r["wall_latency_ns"] for r in self._calls) / 1e9,
            "cache_reused_tokens_total": float(
                sum(r.get("cache", {}).get("reused_tokens", 0) for r in self._calls)
            ),
        }

    def close(self):
        self.clear_caches()
        self.model = None
        if hasattr(self, "torch"):
            import gc

            gc.collect()
            self.torch.cuda.empty_cache()
