# D134: act on complete actions before the whole chunk finishes

The local streaming components pass. A complete VLA action can enter a bounded
JSON-compatible queue while later actions are still being generated. This does
not require retraining or another model. The remaining work is to connect this
boundary to persistent VLM-approved goals and the live simulator controller.

## Measured result

RTX 4060 Laptop 8GB, existing Qwen3-VL-4B NF4 + unmerged D207 step8000 adapter,
Transformers4.57.3, SDPA. Three saved-frame input cases, three repeats each, mode
order rotated; warm-up excluded. These are inference measurements, not flights.

| Mode | Median time | Observed range |
|---|---:|---:|
| Original: wait for eight actions | 3.593 s | 3.437–3.837 s |
| Stream eight: first complete action | 0.565 s | 0.515–0.640 s |
| Stream eight: entire chunk | 3.619 s | 3.462–4.264 s |
| Generate only the first action | 0.552 s | 0.529–0.608 s |

Generating only the consumed action reduces measured waiting time about6.5x.
Streaming does not speed up generation of all eight actions; it exposes the first
one earlier. All288 full-chunk token comparisons and all nine first-action prefixes
match the original generation exactly, including decoded action values. The trained
eight-action input format is unchanged. Three input contexts do not prove universal
equivalence or task quality, and nine repetitions do not certify tail latency.

The separate GPU worker was also exercised with a20Hz control-tick surrogate:
maximum measured tick gap50.77ms, including model startup. First cold worker action
arrived1.044s after submission. A subsequent warm eight-action request delivered
actions at0.549s and1.012s, then cancelled at the original1.5s observation lifetime.
Both queued actions were consumed before expiry. No third action was accepted.
The1.5s lifetime was not extended to finish the chunk. This demonstrates delivery
and responsiveness, not controller execution, obstacle avoidance or flight safety.

One model allocation per owner; direct-model and worker probes run sequentially.
Peak PyTorch allocated4,470,585,344bytes; reserved5,098,176,512bytes. All parameter
version counters stayed unchanged, parameters ended frozen and base text repeated
after adapter use. Version counters are not a cryptographic weight comparison.
The worker exited; GPU usage returned to12MiB with7,945MiB free.

## What is implemented

- `ActionTokenStream`: four raw tokens become one complete action; no partial
  action or model-generated JSON text is executed.
- `ActionBuffer`: bounded queue, strict ordering, detached JSON-compatible records;
  later actions append after earlier ones have already been consumed.
- `QwenWorker`: separate process owning one base/adapter, one outstanding request,
  nonblocking polling, bounded IPC, explicit errors and cooperative cancellation.
- New first-action development profile; historical profiles keep eight actions.
- Code checker for40 lines/function,1,000 lines/file,5arguments, complexity10,
  12branches. The limits apply to changed files, not an unreviewed claim about all
  legacy code.60 focused CPU tests pass; regular Ruff and code-limit checks pass.

The [actual action record](action_record_example.json) includes request/goal ID,
original image sequence and monotonic timestamp, expiry, index, raw tokens and
decoded forward/right/up metres plus clockwise yaw radians. `consumed_ns` is
consumer evidence. These timestamps belong to this run and cannot be replayed as
fresh commands in another run.

On a monitor hold, new goal or camera expiry, revoke both work and buffered actions.
Appending a later action never renews the camera lifetime. The eventual controller
must also enforce current motion constraints and hold/brake when the queue is empty.
Actions are relative deltas, not arbitrary JSON text to send to a motor interface.

## Failed check retained and repaired

`real_v1/result.json` is preserved with `passed:false`. Its token/action checks
passed, but PEFT's adapter context re-enabled gradient flags on exit. No parameter
version changed and inference ran without autograd; no optimization occurred.
The backend now freezes parameters inside and after role switching, including
exceptions. A focused regression reproduces the flag toggle. `real_v2` repeats
the full probe and passes the frozen-parameter and explicit worker checks as well.
No packages were upgraded; existing PEFT configuration-field warnings remain.

## Research and next implementation

The [review](../../docs/research/20261016_latency/DECISION.md) contains30 candidates,
26 substantive inspections and18 primary papers. Immediate measured gain comes
from avoiding unused generation. Next profile the output projection and NF4 decode
kernels before trying action-only projection or fixed-shape compilation. AWQ/GPTQ
with faster kernels remains a separate approximate-weight comparison, not a drop-in
assumption. Image pruning can lose small targets; methods requiring a new flow head
or trained corrector are excluded from this no-retraining effort.

Next integration: VLM authorizes a persistent goal; pilot refreshes from current
frames without calling VLM on every action; planner/monitor run on relevant events.
Connect queue consumption to the shield and a wall-clock controller. Existing
SimClock orchestration stays separate; its synchronous profile is not made
asynchronous by this worker alone. The Project AirSim adapter remains a placeholder.
Grounding, cognitive tasks, live controller scheduling and actual mission completion
remain unverified. No AWS, training, simulator flight or model publication occurred.

Evidence: `real_v2/result.json`, `pairs.json`, saved config and
`verification_local.json` (independent raw comparisons and source/input hashes).
Run `scripts/diagnostics/probe_qwen_stream.py --help` for the bounded reproduction
command. Use a new output directory; do not overwrite the retained failed probe.
