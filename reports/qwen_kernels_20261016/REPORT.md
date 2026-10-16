# D138 — local kernel/cache benchmark:200ms not reached

The bounded saved-input experiment completed. Fused efficient attention with an
explicit grouped-query head expansion gives a modest gain; static cache alone
adds little. No production runtime configuration was changed or promoted.
No flights, AWS, training, downloads, package installations or freshness changes.

## Same-session comparison

100 alternating-order matched requests per supported option: four saved contexts,
25 repetitions each. Warmup, attention instrumentation and eligibility calls are
excluded. Measurements cover preprocessing through first complete four-token
backend callback; they do not include a new camera capture or worker IPC.

| Variant | Median first action | Empirical p95 | Tokens/decoded actions matching paired baseline |
|---|---:|---:|---:|
| Existing dynamic-cache SDPA |2167.8ms|2310.6ms|100/100|
| Expanded KV heads + forced efficient attention |2036.7ms|2201.4ms|100/100|
| Static generation cache |2100.4ms|2237.1ms|100/100|

Median per-pair speedup is1.060x for efficient attention and1.035x for static cache.
These are descriptive results over four repeated contexts, not100 independent
flight situations. The expanded-head path does not meet even the existing1.5s
freshness threshold in this session. Diagnostic actions were discarded.

**The earlier slow session recurred:** baseline is about2.17s here, versus D136's
historical actual-worker0.531–0.572s. That slowdown exists before the experimental
changes. Do not compare this candidate directly against historical0.55s or claim
these modifications caused/fixed the slowdown. The session's causal explanation
remains unresolved. No200ms or end-to-end qualification is claimed.

## Concrete findings

- All observed SDPA Q/K/V tensors were BF16. Vision has16 heads; text queries32
  heads versus8 key/value heads. Runtime inspection rules out FP32 SDPA inputs as
  the explanation for this captured fallback, not every conversion elsewhere.
- Forced FlashAttention fails with the explicit installed-build warning:
  `Torch was not compiled with flash attention.`
- Forced efficient attention rejects unequal query/key/value head counts. The
  diagnostic repeats KV heads as grouped-query attention requires, disables its
  GQA flag and forces efficient SDPA. This runs and matches sampled action tokens.
  Fused floating-point arithmetic is not proven bitwise-logit identical generally.
- Static cache works but is not a compiled decoder. No compiler speedup is claimed.
- A tiny torch.compile CUDA probe stalled and was interrupted; evidence from its
  preceding checks is retained in probe_host/. Subsequent inspection finds no
  installed Triton. We did not install a new runtime to bypass this limitation.
  Manual model CUDA-graph capture was not attempted, so this is not proof that all
  CUDA graph approaches are impossible on Windows.

## Preservation and checks

One model load in the completed benchmark;1,425 parameter objects on CUDA,
unchanged parameter version counters, all parameters frozen. Peak PyTorch allocation
4,470,585,344bytes. No checkpoint writes or optimizer calls. Production shared_qwen
source is unchanged. Base planner/direction/monitor brief text responses match
across variants, and return-to-pilot actions match. These brief role checks do not
qualify visual cognition or mission success.

30 focused tests pass; both diagnostic scripts pass Ruff and the repository's
function/file/argument/complexity limits. Completed process exited0; GPU memory
returned to12MiB. No model left running. The initial sandbox launch and first
compiler attempt were interrupted; neither is counted as a completed benchmark.

Telemetry shows Normal process priority, all24 logical CPUs in affinity, Balanced
power plan, and sampled GPU temperatures around49C. Samples show low GPU utilization
and varying clocks. They do not identify the slowdown's cause; no power, clocks,
thread-count or priority settings were changed. See telemetry.json and host_state.json.

## Decision and next work

Retain the working production configuration and existing1.5s freshness guard.
Neither tested change solves the200ms goal, and the small gain is not justification
for silently changing numerical behavior across all roles.

Next useful local work is to isolate the recurring slow session with per-stage
CPU/GPU timing and launch-context comparison. After establishing a stable baseline,
an isolated runtime with working fused-attention/compiler support can test the
larger acceleration hypothesis. That is a new environment experiment, not something
this report claims to have implemented. No further flight or cloud run is queued.

Evidence: paired/pairs.json, attention.json, eligibility.json, compiler.json,
roles.json, complete.json; verification_local.json; checks.json and source_hashes.json.
Reproduce with a new output directory using scripts/diagnostics/probe_qwen_kernels.py
and the installed GPU Python, PYTHONPATH=src. The watchdog is1200s after argument
parsing; outputs contain saved-camera inputs and actions for diagnostics only.
