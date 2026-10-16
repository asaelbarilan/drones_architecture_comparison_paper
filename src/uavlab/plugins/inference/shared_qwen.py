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
from contextlib import contextmanager, nullcontext
from pathlib import Path

from uavlab.core.registry import register
from uavlab.interfaces import InferenceRequest, InferenceResult

from .qwen_actions import (
    ACTION_CHANNELS,
    CHUNK_ACTIONS,
    action_logits,
    decode_actions,
    encode_pilot,
    read_pilot,
)


@register("inference", "shared_qwen_vla")
class SharedQwenInference:
    ROLES = frozenset({"planner", "direction", "monitor", "pilot"})

    def __init__(self, package_path: str, **options):
        self.package = Path(package_path)
        self.precision = options.get("precision", "nf4")
        self.model_id = options.get("model_id", "qwen3-vl-4b-d207-shared")
        self.max_new_tokens = int(options.get("max_new_tokens", 192))
        self.pilot_actions = options.get("pilot_actions", CHUNK_ACTIONS)
        if type(self.pilot_actions) is not int or not 1 <= self.pilot_actions <= CHUNK_ACTIONS:
            raise ValueError("pilot_actions must fit the trained chunk")
        audit_path = options.get("audit_path")
        self.audit_path = Path(audit_path) if audit_path else None
        self._lock = asyncio.Lock()
        self.model = None
        self.load_count = 0
        self._services = None
        self._calls = []
        self.reuse = None
        self.graphs = None
        self.use_graphs = bool(options.get("pilot_cuda_graphs", False))
        if self.use_graphs and (self.precision != "nf4" or options.get("cache_reuse", False)):
            raise ValueError("Pilot graphs require NF4 and no optional cache reuse")
        if options.get("cache_reuse", False):
            from .qwen_cache import QwenReuse

            self.reuse = QwenReuse(
                kv_bytes=int(options.get("kv_cache_mib", 256) * 1024**2),
                vision_bytes=int(options.get("vision_cache_mib", 64) * 1024**2),
                max_tokens=options.get("cache_max_tokens", 1024),
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
        self._prepare_package()
        self._load_model()

    def _prepare_package(self):
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

    def _load_model(self):
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
        if self.use_graphs:
            from .qwen_graph import PilotGraphs

            self.graphs = PilotGraphs(self)
            self.graphs.prepare()

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

    def _pilot(self, request, delivery=None):
        from .action_stream import ActionTokenStream

        data = read_pilot(request)
        batch = encode_pilot(self, request, data)
        count = self.pilot_actions if delivery is None else delivery.actions
        extra = (
            {} if delivery is None else {"streamer": ActionTokenStream(self.tokenizer, delivery)}
        )
        output = self._generate(
            request,
            batch,
            do_sample=False,
            min_new_tokens=count * ACTION_CHANNELS,
            max_new_tokens=count * ACTION_CHANNELS,
            logits_processor=action_logits(self.tokenizer),
            use_cache=True,
            pad_token_id=self.processor.tokenizer.pad_token_id,
            **extra,
        )
        ids = output[0, batch["input_ids"].shape[1] :].tolist()
        return {
            "steps_fru_m_yaw_rad": decode_actions(self.tokenizer, ids, count),
            "tokens": ids,
            "remaining_supplied": data["remaining"],
        }, len(ids)

    def stream_pilot(self, request, delivery):
        """Synchronous single-owner entry point for the external GPU worker."""
        if request.role != "pilot" or request.model_id != self.model_id:
            raise ValueError("pilot stream requires matching role/model")
        self._load()
        started = time.perf_counter_ns()
        try:
            with self.torch.inference_mode():
                payload, count = self._pilot(request, delivery)
        except BaseException:
            self.clear_caches()
            raise
        elapsed = time.perf_counter_ns() - started
        self._record(request, payload, elapsed)
        return payload, count

    def _generate(self, request, batch, **kwargs):
        batch = self.api.cuda(batch)
        if self.use_graphs and request.role == "pilot":
            from .qwen_graph import PilotGraphs

            if self.reuse is not None:
                raise ValueError("Pilot graphs with optional cache reuse are not validated")
            if self.graphs is None:
                self.graphs = PilotGraphs(self)
            with self.graphs.active():
                return self.model.generate(**batch, **kwargs)
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
        # Serialize before entering this context; no second role may switch it mid-call.
        with self._role_mode(request.role), self.torch.inference_mode():
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

    @contextmanager
    def _role_mode(self, role):
        mode = nullcontext() if role == "pilot" else self.model.disable_adapter()
        try:
            with mode:
                # PEFT adapter switching can re-enable module gradients.
                self.model.requires_grad_(False)
                yield
        finally:
            self.model.requires_grad_(False)

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
            self._record(request, payload, elapsed)
            # Real elapsed inference is charged. No cheap simulated latency claim.
            if self._services:
                await self._services.clock.sleep_ns(elapsed)
            return InferenceResult(payload=payload, output_tokens=tokens, latency_ns=elapsed)

    def _record(self, request, payload, elapsed):
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
        self.graphs = None
        self.model = None
        if hasattr(self, "torch"):
            import gc

            gc.collect()
            self.torch.cuda.empty_cache()
