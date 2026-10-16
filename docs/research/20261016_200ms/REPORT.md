# Can this pilot reach a fresh action in 200 ms?

Research date: 2026-10-16. **Possibly, but not demonstrated. Optimize the execution
runtime first; do not retrain or replace the pilot yet.** A 550-to-200 ms reduction
requires about 2.75 times faster delivery. No inspected source establishes that
speedup for our Qwen3-VL4B + D207 NF4 pilot on RTX4060 Laptop8GB.

## What our measurements actually say

D136's actual worker delivers warm complete actions in 531–572 ms. A separate
five-warm-call saved-input breakdown has medians: first token 189 ms, complete
four-token action 514 ms, remaining three tokens 325 ms (local_analysis.json).
Those backend timings exclude some end-to-end costs and are not a p95 estimate.
Even deleting the entire first-token interval would leave 325 ms if decode stayed
unchanged. Faster image processing alone therefore cannot meet 200 ms. Image/token
changes can also affect later decode, but that benefit requires measurement.

The instrumented profile contains math SDPA and many conversion/copy operations.
It is a diagnostic lead, not a reliable allocation of the uninstrumented 550 ms.
The loader selects `sdpa`; this does not prove a fused kernel ran. Inspect per-layer
Q/K/V dtypes, masks, shapes and backend rejection reasons before changing anything.

Source inspection also prevents a misleading diagnosis: PEFT preparation upcasts
nonquantized parameters, but the packaged trainer setup subsequently casts frozen
FP32 parameters back to BF16. We cannot simply blame that preparation function.
Adapter loading and actual attention activations still need runtime inspection.

## Options, evidence and priority

| Priority | Mechanism | Why / boundary |
|---|---|---|
| 1 | Diagnose math-attention fallback and redundant conversions | Local profile plus N01/D03/D06. Use installed PyTorch fused SDPA where eligible before installing another library. Numeric outputs may differ; no guaranteed speedup. |
| 2 | Fixed-shape decode, static cache and compile/CUDA graphs | D01. Reduces interpreter/kernel-launch work; NF4, PEFT, MRoPE and Windows compatibility must be tested. Separate startup compilation from warm latency. |
| 3 | Pilot-only projection onto valid action-token rows | Local action mask/model structure. Avoid computing unused vocabulary logits, preserving adapter head weights and token mapping. Profile head share first; no published gain claimed. |
| 4 | Optimized INT4 kernels via AWQ/GPTQ/Marlin | L03/L06/L07. Already using NF4 does not mean fastest kernels. Requantization changes weights numerically and needs calibration/quality evaluation; not a configuration-only replacement. |
| Research fallback | Verify proposed action tokens from the preceding action under the fresh image | S02: batched causal verification can reduce sequential passes. Prior-action proposal is our hypothesis, not a demonstrated UAV method. Reject mismatches and fall back; never execute unverified stale proposals. |

For greedy decoding, proposal verification must reproduce the current model's
argmax at each accepted position. Stochastic decoding needs correct acceptance and
residual sampling, not a likelihood threshold. Mathematical distribution preservation
does not promise fixed-seed identity or NF4 batch-shape numerical equality. D133's
failed partial-cache equivalence is direct local counterevidence to assuming this.

## Why not just use the headline speedups?

- EfficientVLA combines pruning with diffusion-expert acceleration on CogACT;
  our pilot has four serial action tokens and no such diffusion expert (L01).
- SpecPrune's roughly1.46x A800 /1.57x3090 results concern OpenVLA-OFT and LIBERO.
  Its approximate pruning can affect precision-sensitive actions (L02).
- FastV studies visual QA including older Qwen-VL, not our flight policy (N02).
- Marlin supplies an optimized INT4 kernel for Ampere/Ada; its linear-layer gains
  are not gains over our complete NF4 VLA pipeline (L03).
- vla.cpp reports model-dependent gains on3090, sometimes near parity with compiled
  PyTorch. The inspected page says code/paper coming soon and does not establish
  support for our checkpoint. It is a watchlist item, not a ready migration (N03).
- FlashAttention2 supports Ada, but native Windows builds need more testing.
  Newer Hopper/Blackwell-specific paths are not a4060 solution (D06).

Do not multiply unrelated speedups. Server batching/throughput, queued action
execution at5Hz, and receiving a first token in200ms are different from receiving
a fresh, complete movement command in200ms. Streaming quartets is already done.

## Model and architecture constraints

Retain one resident base and the trained pilot adapter; planner/direction/monitor
keep their separate histories and priorities. GPU work is still shared, so measure
pilot queue delay during cognition, not only isolated inference. Do not merge the
pilot adapter into shared base weights and silently change the other roles.
Vision-adapter support, saved embeddings/head and MRoPE are migration requirements.
No whole-base BF16 conversion is assumed to fit8GB with caches and simulator use.

## Bounded local experiment plan — proposed, not executed

1. Freeze current working configuration and saved inputs. Record device clocks,
   memory, temperature, software, cold startup and per-stage timings without the
   heavy profiler. Diagnose actual attention backend and conversion origins.
2. Test eligible fused attention, then fixed-shape decode separately. Test action
   vocabulary projection only if profiling makes it worthwhile. Keep baseline
   selectable; do not combine changes before measuring each.
3. Use at least100 timed requests across saved changed-image/goal contexts with
   warmup separate, plus role-switch sequences. Compare full action tokens/decoded
   actions and base-role outputs; retain input/weight identities. Report p50/p95,
   queue time, capture-to-delivery time, memory, fallback and recompilation counts.
4. Claim200ms only when fresh complete-action end-to-end p95 meets200ms on that
   stated test workload. Any smaller gain is reported honestly. Preserve1.5s
   expiry, revocation and stop behavior; no flights during these runtime tests.
5. If precision or quantization changes outputs, label approximate and require a
   separate task-quality decision. Do not call matching a few actions proof of
   quality. Do not install a new stack or spend on AWS to rescue a failed test.

Falsification: abandon an optimization if speed gain disappears outside profiling,
if p95 worsens from compilation/role contention, if it offloads to CPU or exceeds
memory, or if the supposedly equivalent path changes actions. If measured decode
still exceeds200ms, report the attained floor and reconsider the target instead
of weakening freshness. These are fixed evaluation rules, not a promised outcome.

## Coverage and reading

The ledger extends the earlier30-source review by four candidates, with explicit
inherited-versus-fresh provenance. EVIDENCE.md and RESOURCES.md retain compatibility
and license gaps. Structural validation is not deployment qualification.

Start with [Transformers inference optimization](https://huggingface.co/docs/transformers/v4.57.3/en/llm_optims),
[PyTorch SDPA](https://docs.pytorch.org/docs/2.6/generated/torch.nn.functional.scaled_dot_product_attention.html),
and [speculative decoding](https://proceedings.mlr.press/v202/leviathan23a.html).
These explain the most relevant execution mechanisms. The best next test is the
local attention/backend audit; no training, AWS, flights or runtime edits were
performed for this research.
