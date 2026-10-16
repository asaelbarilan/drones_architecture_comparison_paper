# D136 — latency recovered; historical slowdown not reproduced

Saved-input tests on 2026-10-16 recover the earlier approximately 0.55-second
first action, including the actual spawned worker after planner/direction/monitor
calls. **Recovery happened before changing production code.** We have not proved
the cause of D135's slower session and must not claim a causal performance fix.
No flights, training, downloads, AWS calls or system power/priority changes ran.

## What changed, and what did not

- The inference backend SHA256 is still
  `a4ada32b291de6b50b3302cab733efdd56333f5fe2495fd41fbe78ea8975552e`, exactly the
  value saved with D134's 0.552-second result. D135 added scheduling around it.
- Both old and new camera inputs are 224x224. Processor pixel tensors have the
  same shape `[256,1536]`; text/image prompt length changes from 137 to 141 tokens.
- In two fresh, single-model processes, old and new inputs are both fast. This
  excludes a reproducible three-to-fourfold input regression in these checks.
- Repeating under the launch context used for the slow run remains fast. The
  actual spawned worker remains fast after base-role/adapter transitions too.
- Current runtime: PyTorch 2.6.0+cu124, Transformers 4.57.3, 16 CPU threads,
  all 1,425 parameter objects on CUDA. No CPU offload observed. No package upgrades
  or thread-count tuning were applied. D135's thread experiment remains negative.
- D135 model loading also took about 18–20 seconds, versus about 5.7 seconds in
  these repeats. That is consistent with a session-wide machine slowdown rather
  than only the planner integration, but it does not identify its cause. Historical
  power/clock/contention telemetry is insufficient to attribute it confidently.

## Measured results

| Check | Cold first action | Warm first action |
|---|---:|---:|
| D134 historical | Separate worker 1.044s | Median 0.552s |
| D135 historical saved-input probes | 3.24 / 3.58s | 1.82–2.21s |
| D136 paired old input, process A | 1.003s | 0.494–0.495s |
| D136 paired new input, process A | Already warmed | 0.515–0.525s |
| D136 paired old input, process B | 1.031s | 0.537–0.580s |
| D136 paired new input, process B | Already warmed | 0.540–0.556s |
| D136 actual worker, seven pilot requests | 1.081s | 0.531–0.572s |
| New startup-check code, saved input | 1.065s | 0.557–0.558s, three samples |

Old-input prefixes match the historical D134 tokens; new-input prefixes match
the historical D135 tokens. The worker delivered 19 complete actions across seven
pilot requests, all before their original deadlines; no action was executed.
It uses one base load. Eight-action requests cancel at the unchanged 1.5-second
deadline. The delivered action list is timing evidence, not a flight trajectory.

CPU/CUDA profiler tables are preserved for the current fast run. Instrumentation
adds substantial overhead, so table totals are not uninstrumented latency claims.
They cannot retrospectively diagnose the missing slow-session trace.

## Operational repair

`live_qwen/latency.py` adds a non-executing startup check to the real mission runner:

1. Keep the vehicle stationary and discard one bounded warmup request.
2. Require three complete warm first actions before the existing 1.5-second limit,
   reserving one control tick (50ms) for delivery. Every probe retains its deadline.
3. Refuse entry to the flight loop on a slow, expired, malformed or failed probe.
4. Discard every diagnostic action; begin actual planning with fresh observations
   and monotonically increasing request IDs afterward.

The diagnostic uses the initial camera and a neutral hold request, not evaluator
target coordinates. Probe timestamps are measurement start times for explicitly
non-executing replay; they never renew an executable camera lease. Both its input
and results are recorded. Normal runtime action expiry and cancellation remain
unchanged. The existing per-request expiry still protects against slowdown after
startup; three samples cannot certify tail latency or guarantee a later flight.

This fixes missing readiness qualification and isolates cold work from motion.
It does **not** prove a fix for the unexplained D135 warm-session slowdown.

## Validation and remaining uncertainty

67 focused tests pass across latency admission, persistent goals, worker IPC,
streaming, shared roles and caches. Tests specifically reject expired samples,
insufficient delivery margin, failed inference and entry into the flight loop
after a failed preflight. Ruff and the changed-file code limits pass. The existing
scripted simulator test now explicitly disables the real-model startup gate;
no simulator flight was rerun in this investigation.

The real worker passed the new qualification function on saved D135 input.
No model/weight optimization was needed to recover current measured latency.
The honest remaining question is why the historical machine session was slower.
If it recurs, the startup check now stops before spending the episode on hover;
capture the slow-session profiler and hardware state then, rather than inventing
a cause or increasing the freshness limit. No follow-on flight is scheduled.

Evidence: `diagnosis/`, `launch_context/`, `worker_replay/calls.json`,
`startup_gate/result.json`, `verification_local.json`. Model processes exited;
GPU usage returned to 12MiB. No paid resources touched.

Reproduce without flight, using a new output directory:

```powershell
$env:PYTHONPATH='src'
& D:/drone_vla_pilot/venv_qwen/Scripts/python.exe scripts/diagnostics/probe_qwen_worker_latency.py --package D:/drone_vla_pilot/release/hf_fresh_d257/model --out reports/qwen_latency_new --gate-only
```
