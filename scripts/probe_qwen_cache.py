"""Bounded, offline cache equivalence probe; no simulator or flight commands.

Run tiny CPU Qwen first, then --mode real for the existing local D207 package.
Output criteria are fixed here: identical greedy tokens; CPU max logit error
1e-5; NF4 GPU first-step max logit error .25 and max probability error .02.
Different prefill matrix shapes can cause BF16 roundoff; never call it exact
logit equality unless the measured error is zero.
"""

import argparse
import base64
import io
import json
import os
import threading
import time
from pathlib import Path

os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def tiny_probe():
    import torch
    from transformers import Qwen3VLConfig, Qwen3VLForConditionalGeneration

    from uavlab.plugins.inference.qwen_cache import QwenReuse

    torch.manual_seed(1061)
    torch.set_num_threads(2)
    config = Qwen3VLConfig(
        text_config=dict(
            vocab_size=128,
            hidden_size=64,
            intermediate_size=128,
            num_hidden_layers=4,
            num_attention_heads=4,
            num_key_value_heads=2,
            head_dim=16,
            rope_scaling=dict(rope_type="default", mrope_section=[2, 3, 3]),
        ),
        vision_config=dict(
            depth=2,
            hidden_size=32,
            intermediate_size=64,
            num_heads=4,
            out_hidden_size=64,
            patch_size=16,
            spatial_merge_size=2,
            temporal_patch_size=2,
            num_position_embeddings=64,
            deepstack_visual_indexes=[0, 1],
        ),
        image_token_id=100,
        video_token_id=101,
        vision_start_token_id=102,
        vision_end_token_id=103,
        eos_token_id=127,
        pad_token_id=0,
    )
    model = Qwen3VLForConditionalGeneration(config).eval()
    reuse = QwenReuse(kv_bytes=64 * 1024, vision_bytes=16 * 1024, max_tokens=32)
    patches = torch.randn(16, 3 * 16 * 16 * 2)

    def batch(image=patches, prompt=25, two=False):
        ids = [1, 2, 3, 4, 5, 6, 7, 8, 102] + [100] * 4 + [103]
        if two:
            ids += [102] + [100] * 4 + [103]
        ids += [20, 21, 22, prompt, 24]
        x = torch.tensor([ids])
        return dict(
            input_ids=x,
            attention_mask=torch.ones_like(x),
            pixel_values=torch.cat([patches, image]) if two else image,
            image_grid_thw=torch.tensor([[1, 4, 4]] * (2 if two else 1)),
        )

    options = dict(
        do_sample=False,
        min_new_tokens=4,
        max_new_tokens=4,
        use_cache=True,
        return_dict_in_generate=True,
        output_scores=True,
    )
    rows = []
    cases = [
        ("cold", "direction", batch()),
        ("repeat", "direction", batch()),
        ("changed_text", "direction", batch(prompt=26)),
        ("other_role", "monitor", batch()),
        ("other_mode", "pilot", batch()),
        ("base_after_pilot", "direction", batch(prompt=26)),
        ("changed_pixels", "direction", batch(image=patches + 1)),
        ("two_images", "monitor", batch(two=True)),
        ("keyframe_then_new_latest", "monitor", batch(image=patches + 1, two=True)),
    ]
    with torch.inference_mode():
        for name, role, data in cases:
            fresh = model.generate(**data, **options)
            cached = reuse.generate(
                model, data, role, "pilot" if role == "pilot" else "base", **options
            )
            # Min-length generation deliberately masks EOS to -inf on both sides.
            same_mask = all(
                torch.equal(torch.isfinite(a), torch.isfinite(b))
                for a, b in zip(fresh.scores, cached.scores, strict=False)
            )
            error = (
                max(
                    (a[torch.isfinite(a)] - b[torch.isfinite(a)]).abs().max().item()
                    for a, b in zip(fresh.scores, cached.scores, strict=False)
                )
                if same_mask
                else float("inf")
            )
            rows.append(
                dict(
                    case=name,
                    tokens_equal=torch.equal(fresh.sequences, cached.sequences),
                    max_logit_error=error,
                    cache=dict(reuse.last),
                )
            )
    # Error cleanup must remove hooks and restore native methods, not poison the next call.
    native = model.model.get_image_features
    native_decoder = model.model.language_model.forward
    decode_calls = 0

    def fail(_module, _args, output):
        nonlocal decode_calls
        decode_calls += 1
        if decode_calls == 2:
            raise RuntimeError("injected failure after extending cached prefill")

    handle = model.model.language_model.register_forward_hook(fail)
    try:
        with torch.inference_mode():
            reuse.generate(model, batch(image=patches + 1, two=True), "monitor", "base", **options)
    except RuntimeError:
        pass
    finally:
        handle.remove()
    restored = model.model.get_image_features == native
    cleared = reuse.kv.bytes == reuse.vision.bytes == 0
    hooks_removed = model.model.language_model.forward == native_decoder
    with torch.inference_mode():
        model.generate(**batch(), **options)
        # Reused prefill must still decode anew with a different output budget.
        reuse.generate(model, batch(), "direction", "base", **options)
        shorter = dict(options, min_new_tokens=2, max_new_tokens=2)
        fresh = model.generate(**batch(), **shorter)
        cached = reuse.generate(model, batch(), "direction", "base", **shorter)
        different_budget = torch.equal(fresh.sequences, cached.sequences)
    # Independent physical-storage audit catches views retaining larger buffers.
    actual_storage = sum(
        sum(
            x.keys.untyped_storage().nbytes() + x.values.untyped_storage().nbytes()
            for x in entry[1].layers
        )
        + entry[2].untyped_storage().nbytes()
        for entry, _size in reuse.kv.entries.values()
    )
    storage_exact = actual_storage == reuse.kv.bytes
    passed = all(r["tokens_equal"] and r["max_logit_error"] <= 1e-5 for r in rows)
    passed &= rows[1]["cache"]["reused_tokens"] > 0
    passed &= rows[3]["cache"]["reused_tokens"] == 0 and rows[3]["cache"]["vision_hit"]
    passed &= not rows[4]["cache"]["vision_hit"]
    passed &= rows[6]["cache"]["reused_tokens"] == 0
    passed &= rows[8]["cache"]["reused_tokens"] == 0
    return dict(
        passed=bool(
            passed
            and restored
            and cleared
            and hooks_removed
            and different_budget
            and storage_exact
            and decode_calls == 2
        ),
        cases=rows,
        exception_cleanup=dict(restored=restored, cleared=cleared, hooks_removed=hooks_removed),
        different_generation_budget=different_budget,
        retained_storage_accounting=storage_exact,
    )


def real_probe(out):
    import torch
    from PIL import Image, ImageEnhance

    from uavlab.interfaces import InferenceRequest
    from uavlab.plugins.inference.qwen_cache import QwenReuse
    from uavlab.plugins.inference.shared_qwen import SharedQwenInference

    backend = SharedQwenInference(
        "D:/drone_vla_pilot/release/hf_fresh_d257/model", max_new_tokens=16
    )
    cache = QwenReuse()
    rows = []
    backend._load()
    original = backend.model.generate
    capture = {}

    def generate(**kwargs):
        value = original(**kwargs, return_dict_in_generate=True, output_scores=True)
        capture["tokens"] = value.sequences[0, kwargs["input_ids"].shape[1] :].tolist()
        capture["logits"] = value.scores[0].detach().float().cpu()
        return value.sequences

    backend.model.generate = generate
    source = Image.open("reports/shared_qwen_vla_20261016/final/input.png").convert("RGB")

    def encode(image):
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()

    a = encode(source)
    b = encode(ImageEnhance.Brightness(source).enhance(0.7))
    c = encode(source.resize((320, 256)))

    def request(role, prompt, images=()):
        return InferenceRequest(
            model_id=backend.model_id,
            role=role,
            prompt_hash="d133-probe",
            prompt=prompt,
            images=images,
            image_count=len(images),
            observation_seq=1,
        )

    planner = request("planner", "Reply with exactly one word: ready.")
    direction = request("direction", "Describe the image in five words.", (a,))
    monitor = request("monitor", "Is a red tower visible? Answer yes or no.", (a,))
    pilot = request(
        "pilot",
        json.dumps(
            dict(
                instruction="Move forward 2 meters.",
                state=[0, 0, 0, 0],
                remaining=[2, 0, 0, 0],
                box=None,
            )
        ),
        (a,),
    )
    cases = [
        ("planner_cold", planner),
        ("planner_repeat", planner),
        ("direction_cold", direction),
        ("direction_repeat", direction),
        ("monitor_shared_image", monitor),
        ("monitor_repeat", monitor),
        ("pilot_cold", pilot),
        ("pilot_repeat", pilot),
        ("planner_after_pilot", planner),
        ("direction_after_pilot", direction),
        (
            "direction_changed_text",
            request("direction", "Describe the image in three words.", (a,)),
        ),
        ("direction_changed_pixels", request("direction", direction.prompt, (b,))),
        ("direction_changed_grid", request("direction", direction.prompt, (c,))),
        (
            "monitor_two_images",
            request("monitor", "Describe the differences in five words.", (a, b)),
        ),
        (
            "monitor_new_latest",
            request("monitor", "Describe the differences in five words.", (a, c)),
        ),
    ]
    try:
        for name, req in cases:
            pair = []
            for use_cache in (False, True):
                backend.reuse = cache if use_cache else None
                torch.cuda.synchronize()
                start = time.perf_counter()
                payload, _ = backend._run(req)
                torch.cuda.synchronize()
                pair.append(
                    dict(
                        tokens=capture["tokens"],
                        logits=capture["logits"].clone(),
                        payload=payload,
                        seconds=time.perf_counter() - start,
                    )
                )
            fresh, cached = pair
            finite = torch.isfinite(fresh["logits"]) & torch.isfinite(cached["logits"])
            same_mask = torch.equal(
                torch.isfinite(fresh["logits"]), torch.isfinite(cached["logits"])
            )
            error = (fresh["logits"][finite] - cached["logits"][finite]).abs().max().item()
            prob_error = (
                (fresh["logits"].softmax(-1) - cached["logits"].softmax(-1)).abs().max().item()
            )
            row = dict(
                case=name,
                role=req.role,
                tokens_equal=fresh["tokens"] == cached["tokens"],
                payload_equal=fresh["payload"] == cached["payload"],
                max_first_logit_error=error,
                max_first_probability_error=prob_error,
                same_finite_mask=same_mask,
                fresh_seconds=fresh["seconds"],
                cached_seconds=cached["seconds"],
                fresh_tokens=fresh["tokens"],
                cached_tokens=cached["tokens"],
                cache=dict(cache.last),
            )
            row["passed"] = bool(
                row["tokens_equal"]
                and row["payload_equal"]
                and same_mask
                and error <= 0.25
                and prob_error <= 0.02
            )
            rows.append(row)
            # Store numerical evidence separately from the concise report.
            import numpy as np

            np.savez_compressed(
                out / f"{name}_logits.npz",
                fresh=fresh["logits"].numpy(),
                cached=cached["logits"].numpy(),
            )
            (out / "progress.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
            print(json.dumps(row), flush=True)
        contracts = dict(
            repeat_hits=all(rows[i]["cache"]["reused_tokens"] > 0 for i in [1, 3, 5, 7, 8, 9]),
            cross_role_vision=rows[4]["cache"]["vision_hit"]
            and rows[4]["cache"]["reused_tokens"] == 0,
            pilot_vision_isolated=not rows[6]["cache"]["vision_hit"],
            changed_pixels_miss=not rows[11]["cache"]["vision_hit"],
            changed_grid_miss=not rows[12]["cache"]["vision_hit"],
            bounded=cache.kv.bytes <= cache.kv.max_bytes
            and cache.vision.bytes <= cache.vision.max_bytes,
            one_load=backend.load_count == 1,
        )
        return dict(
            passed=all(r["passed"] for r in rows) and all(contracts.values()),
            cases=rows,
            contracts=contracts,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_reserved_bytes=torch.cuda.max_memory_reserved(),
            kv_bytes=cache.kv.bytes,
            vision_bytes=cache.vision.bytes,
            kv_evictions=cache.kv.evictions,
            transformers_version=__import__("transformers").__version__,
        )
    finally:
        backend.model.generate = original
        cache.clear()
        backend.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["tiny", "real"], required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Choose a fresh evidence directory")
    args.out.mkdir(parents=True)
    watchdog = threading.Timer(600, lambda: os._exit(124))
    watchdog.daemon = True
    watchdog.start()
    result = dict(passed=False, mode=args.mode, scope="offline cache test; no flights/training/AWS")
    try:
        result.update(tiny_probe() if args.mode == "tiny" else real_probe(args.out))
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        (args.out / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        watchdog.cancel()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["passed"] else 1)
