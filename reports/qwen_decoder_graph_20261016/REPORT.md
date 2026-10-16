# D-142: local first-action acceleration toward 200 ms

2026-10-16–17. Saved-input diagnostics only; no flights, AWS or training.

## Result and boundary

The experimental worker delivers a complete four-token action in **198.06 ms
warm median** with 2 ms queue polling, across 20 warm pilot requests interleaved
with planner, direction and monitor calls. Range195.19–202.91 ms; empirical
p95=200.07 ms. This meets the typical-latency target, not a guaranteed200 ms
deadline. First request after prepared readiness199.79 ms. Startup model loading,
graph capture and discarded equality checks are excluded from warm latency.
These are recorded images, not camera-to-actuator or simulator-load timings.

| Measurement | Median | Empirical p95 | Scope |
|---|---:|---:|---|
| D141 reference, same-session paired backend |348.66 ms|377.08 ms|96 warm pairs|
| D142 candidate, same-session paired backend |193.57 ms|195.19 ms|96 warm pairs|
| D142 worker produces action, 20 ms consumer poll |195.95 ms|199.78 ms|20 warm calls|
| D142 worker delivered, 20 ms consumer poll |205.82 ms|209.20 ms|same20 calls|
| D142 worker delivered, 2 ms consumer poll |198.06 ms|200.07 ms|separate20 warm calls|

100 paired first actions (four saved contexts,25 repetitions, alternating A/B
order) match exact token IDs and decoded actions; first repetition excluded from
warm statistics. Four additional complete32-token chunks also match. Each worker
run independently checks two full chunks before readiness. All30 mixed-role
outputs match D141 base-role outputs/common action prefixes. Prefix equality
alone does not imply full-chunk equality; the separate chunk tests establish
that narrower claim. This is repeated testing of few contexts, not100 distinct
tasks or proof of flight quality. Output probabilities were not tested bitwise.

The existing latency qualification gate also passes, with delivered times
202–208 ms in the final run. Its separate polling loop is unchanged. Neither
the1.5 s freshness bound nor the20 Hz controller was changed. The2 ms consumer
poll belongs only to the diagnostic; production integration remains pending.

## What changed

Isolated diagnostic backend, same frozen NF4 Qwen base and trained adapter:

1. Capture larger fresh vision, prompt-prefill and autoregressive decode GPU
   graphs instead of D141's small projection/MLP graphs.
2. Compute only the256 permitted action output rows, retaining their original
   weights and greedy selection; other vocabulary logits are masked out.
3. Generate the remaining three tokens of the first action in one GPU replay,
   then subsequent four-token actions. No predicted/skipped token or JSON proxy.
4. Size the static KV buffer to256 tokens for these short requests, instead of
   512. Overflow raises an error; it never truncates the instruction or image.
5. Measure queue delivery with both original20 ms and explicit2 ms polling.

The KV cache resets every request; fresh image tensors, embeddings, masks and
positions are copied into graph buffers. This is not reuse of an old observation.
Pilot-only patches are restored in finally blocks; base roles use original
generation. Cancellation/expiry is checked before each complete action is
released. A running GPU burst is not preemptible token-by-token. One model load,
all parameters frozen, parameter versions unchanged. Peak allocated4,470,585,344
bytes and reserved5,645,533,184 bytes in the paired D141/candidate process.

## Attempts and limits

The preserved progression is initial text-decode graph (~272 ms), fresh vision
graph (~232 ms), prefill graph (~216 ms), action-only head (~203 ms), and burst
path (~201 ms with512-token KV). These short preliminary tests are not equivalent
to the final longer test. Initial burst prototype failed on a missing explicit
cache_position; failure evidence remains under burst/. The repaired run is
burst_positions/. No flight was attempted with the failed prototype.

Thread counts1/2/4/8/16, head fusion, dense vision-position insertion, expanded
efficient attention, TF32 and BF16 norm storage were screened. Several yielded
negligible or noisy incremental benefits. TF32 and norm precision are not enabled
in the final candidate. The norm probe required exactly representable stored
values and restored them after each request; it did not improve latency.
The retained candidate makes no additional weight-precision conversion.

Synchronized512-cache profile: image encoding CPU~3.5 ms, visionGPU~17 ms,
three decode tokens~62.5 ms, and roughly110 ms in remaining prefill work. Timing
hooks perturb execution; profile values are diagnostic, not benchmark claims.
The256-cache result is the final measured configuration, not a subtraction from
those profile figures. No lower-resolution image or reduced context was used.

Prototype assumptions: installed Transformers4.57.3/Torch2.6.0+cu124, single
unpadded image request, greedy action generation, trained action vocabulary,
short prompt within capacity, serialized access, prepared graph shapes. This
code is under scripts/diagnostics; production defaults and architecture code
are unchanged. Before deployment it needs bounded shape handling/fallbacks,
readiness coverage and integrated controller/event-dispatch qualification.
No claim of general mission performance or hard200 ms tail latency.

## Evidence and reproduction

- final_256/pairs.json and verification.json:100 pairs, four full chunks and
  model invariants; reference explicitly uses D141 pilot_cuda_graphs=True.
- worker_256/ and worker_256_poll2/: mixed-role calls, readiness equality and
  unchanged qualification gates; verification_local.json includes other trials.
- profile/, worker_tf32/, worker_norm_precision/, threads/: rejected/limited
  alternatives retained, not silently folded into the successful configuration.
-33 focused tests pass: graph freshness/shape rejection, role restoration,
  action streaming/cancellation, worker isolation and latency gates. Changed
  Python files pass repository function-size/complexity limits and Ruff.

Run with local GPU Python, PYTHONPATH=src, the existing offline model package:

```powershell
python scripts/diagnostics/verify_qwen_full_graph.py --package <package> --out <new-directory> --cache-tokens 256
python scripts/diagnostics/probe_qwen_fast_worker.py --package <package> --out <new-directory> --cache-tokens 256 --poll-ms 2
python scripts/diagnostics/summarize_qwen_full_graph.py
```

RTX4060 Laptop8GB, process performance-core placement and latency QoS. No package
install, global power change, model-file writes or extra base model. GPU unloaded
after tests (12 MiB,0% utilization). Next step is careful optional integration
and simulator-load timing, not further quantization or a claim that the existing
flight runtime already delivers every action in200 ms.
