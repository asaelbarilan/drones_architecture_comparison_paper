# D-133: bounded cache reuse on the local shared Qwen model

The conservative implementation passes all 15 real-model comparisons: identical
generated token sequences, decoded outputs/actions, and first-step logits. One
Qwen3-VL-4B NF4 base and the existing unmerged D207 step8000 adapter were used.
No weights changed, no flights or AWS calls were run, and the GPU process exited.

## What is enabled

Use `shared_qwen_vla_cached_dev`; `shared_qwen_vla_dev` remains the uncached control.
Each role owns its own exact prompt prefill KV plus the last prompt hidden state.
Generated-answer KV is removed before storage; every response is decoded anew.
Changing the generation budget still works. Base roles share image features for
identical **ordered, processed image batches**. Pilot image features are separate
because its adapter changes the visual encoder too. There is no cross-role KV reuse.

Identity includes loaded base instance, adapter mode, actual input token IDs,
all three multimodal position axes, pixel tensor hashes and image grid/order.
The caller's prompt hash, observation ID or image placeholder IDs alone are never
accepted as evidence of identical inputs. Qwen recomputes multimodal positions
for each full request, so a previous role's RoPE state cannot be reused accidentally.

Persistent limits: 256 MiB KV, 64 MiB visual tensors, 1,024 input tokens per retained
role, at most four KV entries and eight visual batches. LRU eviction is bounded by
bytes and entries. Longer inputs run fresh and are not retained. Tensor slices
are compacted; reset, close and failed calls clear caches. These limits cover
retained tensor storage, not model weights, temporary current-call allocations,
Python metadata or the simulator renderer. The supported boundary is pinned to
the locally tested Transformers 4.57.3; it must be revalidated after an upgrade.

## Important limitation: partial-prefix reuse was rejected

The first implementation reused the common prefix and recomputed only the suffix.
It passed a small float32 Qwen test, but failed the full NF4 test: 2/15 cases changed
generated text, and several first-step logit errors exceeded the predeclared 0.25
limit (maximum 0.4765625). Failed evidence remains in `real_v1/`.

The local bitsandbytes implementation selects different arithmetic paths for a
single-token matrix versus a multi-token matrix. Shorter prefills can also change
other matrix/kernel shapes. This is a plausible numerical source; we have **not**
isolated one kernel as the sole cause. No pass threshold was relaxed.

The final implementation avoids recomputing a shorter suffix: it reuses a complete
identical prefill, otherwise does fresh decoder prefill. Stable-prefix-only matches
are logged diagnostically but **not used**. Thus this is a smaller optimization than
OnFly's changing-context prefix reuse. A moving camera usually prevents KV hits;
same-frame sharing between direction and monitor can still save visual encoding.
We do not reuse one image's features inside a differently batched image list, since
that would also require numerical-equivalence validation.

## Evidence and timings

Authoritative GPU evidence: `real_exact/result.json`, its per-case raw logits NPZ
files and `progress.json`. Each of 15 requests ran once fresh and once cached;
these are 30 model calls, not 30 independent tasks. Cases include all four roles,
base→pilot→base switching, changed text/pixels/resolution, and two-image history
with a changed latest frame. All 15 have exact generated tokens and zero measured
first-step logit/probability difference. This does not prove all inputs equivalent.

Examples from warm repeated inputs (one measurement each, not a robust speed benchmark):

| Role / case | Fresh (s) | Cached (s) |
|---|---:|---:|
| Planner repeated prompt | 0.206 | 0.116 |
| Direction repeated image and prompt | 0.602 | 0.464 |
| Monitor repeated image and prompt | 0.248 | 0.124 |
| VLA repeated image/state/goal, 32 tokens | 3.679 | 3.438 |
| Monitor different role, shared image only | 0.251 | 0.217 |
| Monitor history with changed latest image | 0.559 | 0.566 |

The last case demonstrates the limit: changed inputs do not automatically become
faster. Cold-order warmup differences are not counted as cache benefits.
Retained tensors at probe end: 60,919,808 KV bytes + 11,141,120 visual bytes
(about 68.7 MiB total). Peak PyTorch allocated 4,470,585,344 bytes, reserved
5,098,176,512 bytes; neither is an AirSim-inclusive memory benchmark.
Independent post-exit `nvidia-smi`: 12 MiB GPU used, 7,945 MiB free.

39 focused CPU/backend/frame-cache tests pass; lint passes. Tiny-model numerical,
failure-cleanup and storage-accounting evidence is in `tiny_final/result.json`.
The initial `tiny_v1` checker incorrectly subtracted masked -infinity EOS logits;
its NaNs were a checker error, not nonfinite model outputs. `tiny_v2` retained the
corrected float32 partial-prefix diagnostic; `tiny_exact` tested the final approach.

## Next boundary

This does not implement streaming actions, a persistent mission skill graph,
asynchronous GPU scheduling, or live AirSim control. Existing staleness limits and
historical profiles are unchanged. Streaming first complete actions and independent
hover/control remain the next efficiency work; cache reuse alone does not make the
3.4-second pilot or the former serial loop real-time.

Research reference: [OnFly §IV-A3 and §IV-D](https://arxiv.org/html/2603.10682v1).
It shares visual features with separate per-agent KV caches; this development
integration is not a full OnFly reproduction.
