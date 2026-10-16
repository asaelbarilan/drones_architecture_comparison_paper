# D141: local CUDA graphs and low-bit feasibility

CUDA graphs improve saved-input first-action latency without retraining. They do
not reach 200ms. No flights, AWS calls, weight writes, environment upgrades or
freshness changes were made. The ordinary configuration remains unchanged;
`pilot_cuda_graphs=true` is an optional, tested local-worker path.

## Measured result

| Check | Result |
|---|---|
| 100 paired cases, four saved contexts | All action tokens and decoded actions equal |
| Same-session eager warm median / empirical p95 | 0.520 / 0.645 seconds |
| Graph warm median / empirical p95 | 0.346 / 0.411 seconds |
| Actual prepared worker, 20 warm first actions | Median 0.373; range 0.339–0.452; empirical p95 0.436 seconds |
| Prepared worker first cold action | 0.932 seconds after worker ready |
| 30 interleaved pilot/planner/direction/monitor calls | All common action prefixes and base-role outputs match D140 |
| Original startup qualification after replay | Passed; complete actions under unchanged deadline |
| Model | One base load, frozen, parameter versions unchanged in paired probe |
| Peak allocated memory in paired probe | 4,470,585,344 bytes |

The paired warm summary excludes the first four capture calls; all 100 are
included in equality checks. Order is eager then graph, not randomized. Only four
contexts were repeated; this is not a broad accuracy benchmark or live-camera
latency claim. Faster generation can emit more actions before expiry, so worker
comparison uses the common prefix, not falsely equal full chunk lengths.

Initial MLP-only prototype reached 0.446s median. Adding attention projections
reduced CPU dispatch overhead further. Prefill, vision, attention/cache management
and base-role generation stay eager. Per-module graphs receive fresh hidden
states. No previous action, image or KV result is reused.

Initial lazy capture took about 20 seconds and correctly expired its first
request. That failed run is retained under `worker/`. The implementation now
prepares kernels with discarded synthetic tensors before worker readiness;
`prepared_worker/` passes. This moves startup cost, it does not eliminate it.
The initial worker experiment overlapped a small CPU quantization screen; the
prepared-worker replay did not overlap that screen. Shape changes fall back to
eager. Pilot scope restores original forwards on cancellation/errors, preventing
pilot-adapter graph use by base roles. Optional prefix cache reuse is disallowed
with this experimental path. Current default remains the prior working path.

## 2-bit and 1-bit assessment

The working environment has no HQQ, Gemlite or Triton. HQQ 0.2.8.post1 was
downloaded/extracted only into an isolated tmp directory, without installing it.
Archive SHA256 is recorded in `lowbit.json`. A CPU-only reconstruction test used
the first 256 rows of original gate-projection weights from layers 0, 17 and 35,
group size64, axis1, HQQ's non-gradient weight optimization. Original model files
were not modified or requantized from already-NF4 weights.

Relative weight RMSE was 8.8–9.0% at4bits, 43.8–44.2% at2bits, and104–105% at1bit.
These are **weight reconstruction errors, not action error or accuracy loss**.
At these settings packed weights plus FP32 scale/zero metadata used409600,
245760 and163840 bytes respectively per slice. Storage savings alone do not
establish inference speed. No full-model low-bit behavior or speed test passed;
therefore neither 2-bit nor1-bit is qualified for the pilot.

[HQQ](https://github.com/dropbox/hqq) supports selective quantization and a
Gemlite integration. [Gemlite](https://github.com/dropbox/gemlite) supplies low-bit
Triton kernels. Its latest docs include BF16 support, while the HQQ integration
instructions specify FP16 for the low-bit backend: exact version/dtype/adapter
compatibility needs an isolated-stack test, not assumptions from headline speed.

Recommendation: retain current weights and use graphs as the next runtime
candidate. Do not switch to1-bit. Selective2-bit remains research requiring a
separate compatible kernel environment and full role/action quality checks.
200ms remains unproven; larger graph regions may reduce remaining dispatch cost.

## Verification and files

45 focused tests passed (graph isolation, shared roles, worker, cancellation,
latency gate, runtime). Changed Python files pass repository limits and Ruff.
`verification_local.json` contains computed timing/output checks; `projections/`
contains100 pairs and invariants; `prepared_worker/` contains30 actual-worker calls
and qualification; `lowbit.json` contains the bounded quantization screen.
All GPU jobs exited; final observed GPU allocation12MiB, utilization0%.
