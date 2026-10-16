# D135 — asynchronous integration, real-model qualification failed

Persistent goals, streamed actions, event-driven planning/monitoring and the
existing controller/shield are connected in `src/uavlab/live_qwen`. Local
validation completed on 2026-10-16. This is not an admitted autonomous-flight
configuration: neither real-model task completed.

## What changed

- Planner runs at startup or replanning. Direction authorizes an anchored goal.
  Numeric offsets remain relative to the episode origin across replans.
- Pilot chunks use fresh images/state while the goal persists. Complete actions
  enter the bounded JSON queue and can execute before later actions arrive.
- Arrival, stalled progress, shield intervention and a periodic scene check
  request monitoring. Motion pauses during cognition; simulated physics continues.
- One spawned GPU owner serializes model calls using the existing shared base and
  pilot adapter. The parent controller does not await inference. These roles are
  asynchronous with control, not simultaneous GPU generations. Language calls
  cannot be interrupted mid-generation; stale results are discarded.
- Revocation clears buffered and active motion. The independent shield checks
  each control tick. Physics advancement splits at command expiry even after a
  late tick. The original image deadline is never renewed.
- STOP requires acceptable position, heading and speed, plus a terminal goal.
  Reaching an intermediate goal returns to planning with completion history.
- Existing SimClock profiles remain unchanged. No simulator task labels or goal
  truth enter model prompts. Evaluation uses the separately declared task target.

## Verification

63 focused tests passed (runtime, goals, worker, action stream, caches and shared
Qwen). New/changed D135 Python files pass Ruff and the repository limits: functions
at most40 lines excluding docstrings, files at most1,000 lines, five arguments,
complexity10 and12 branches. This does not claim historical files meet those limits.

The complete rendered-grid runtime with **scripted delayed replies** succeeds:
one planner, one direction authorization, four pilot requests, three executed
fresh actions and one monitor. Final position error0.4411m, heading0degrees,
speed0.1400m/s,47 control ticks over2.3987s, maximum gap53.35ms, no collision or
out-of-bounds. This tests software integration, not Qwen behavior.
Evidence: `scripted_runtime/result.json` and its raw events/images.

## Actual shared-Qwen simulator tests

Two60-second wall-paced rendered grid3d runs used the installed local model,
real controller and shield. These are **not AirSim tests**; that adapter remains
unimplemented. Numeric empty-scene tasks do not validate visual grounding or
general cognitive missions.

| Task | Planner / direction / pilot / monitor calls | Executed actions | Final task error | Result |
|---|---|---:|---|---|
| Forward2m | 2 / 2 / 9 / 1 | 0 | 2m | Failed: safe hover |
| Right turn30deg | 2 / 2 / 7 / 1 | 0 | 30deg | Failed: safe hover |

Both authorize numeric goals and the monitor detects stalled progress, triggering
replanning. Every saved command is hold; each run has one unique position and
954 control ticks. No collisions or out-of-bounds. `fresh_actions=true` in the
original summaries is vacuous for zero actions and is NOT an integration pass.
The script exited normally after the test budget; exit0 is not task success.

Pilot generation missed the unchanged1.5s source-image deadline. Saved-input
uncapped first-action probes measured warm1.82–2.21s, with cold3.24/3.58s.
Reducing PyTorch threads16->1 did not consistently improve warm latency; all
probed action-token sequences match. No thread-count change was deployed.
Cause of the difference from D134's earlier0.552s measurement remains unresolved;
that earlier number must not be used as current live performance.

Real_v1 used asyncio sleep and achieved about15.9Hz (maximum gap66.95ms), despite
the requested20Hz. A high-resolution thread sleep replaced it afterward; the
scripted whole-runtime test above validates about19.6Hz. The changed timer has
not been requalified with the real GPU model and cannot be called a live20Hz pass.

Evidence: `real_v1/{forward,turn}/events.jsonl`, exact input PNGs and results;
`thread_probe.json`, `thread_probe_v2.json`; independent `verification_local.json`.
`simulator_audit.png` was visually inspected: actual input camera panels and
role timelines agree with the saved events. No motion/path improvement is claimed.

## Remaining boundary

The integration is implemented and locally exercised, but successful real-model
motion remains blocked by inference latency. Next isolate prefill, NF4 decode and
output projection on the saved input before another flight. Do not lengthen
freshness limits to manufacture movement. Visual grounding and actual AirSim
qualification remain separate and unproven. The legacy first-action SimClock
profile also needs its eight-step consumer compatibility checked; this new runtime
does not use that consumer.

No AWS, retraining, new downloads, cloud calls, publication or resource deletion.
Owned model processes exited and GPU allocation returned to12MiB after probing.

Reproduce only when intentionally running another local test:

```powershell
$env:PYTHONPATH='src'
& D:/drone_vla_pilot/venv_qwen/Scripts/python.exe scripts/diagnostics/run_qwen_async.py --config configs/experiments/qwen_async_local.json --out reports/qwen_async_new
```

The runner refuses an existing output directory and has a360s process watchdog.
