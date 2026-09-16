# D-123: matched 240-second commitment comparison

**Commitment on completed the mission at 71.2 s. Commitment off lost the target,
flew away, and ended in repeated geofence rejections.** Both had the requested
240-second budget and zero collisions. The off run was stopped diagnostically at
175 s after the frozen 45-second repetition condition; its unobserved remainder
must not be counted as a measured 240-second failure.

| Condition | Outcome | End time | Closest distance | Final distance | Collisions |
|---|---|---:|---:|---:|---:|
| Commitment off | Early diagnostic stop; censored | 175.0 s | 13.401 m | 51.182 m | 0 |
| Commitment on, bounded 20 s | Arrival and terminal STOP | 71.2 s | 1.5335 m | 1.5338 m | 0 |

On entered the 2 m radius at 68.95 s. Final speed was 0.0104 m/s. Final environment
samples are one 0.05 s physics step after the runtime termination timestamps.
A sustained hover is not part of this task's success criterion.

## What changed at the branch

These are two fresh GPU flights on development seed 1061, using the same local
Qwen3-VL4B digest, environment, prompts, sampling settings, fixed simulated latencies,
verifier, SUPER planner, controller and stopping rules. Resolved configuration checks
allow only `target_commitment_s` to differ (0 versus 20), apart from display metadata.
Both retain the earlier fresh-image recovery guard. The off condition is therefore
this extension's matched ablation, not an assertion of untouched native-paper fidelity.

Before 36 s, corresponding request images/prompts/schemas and raw model replies match.
All control values and recorded positions match before 37 s. At 35 s both accept the
same VLM target waypoint from the same image. At 36 s both receive the same exploration
proposal during occlusion. Off accepts replacement; on defers it and retains the
already accepted target. The first control difference is at 37 s, after activation.
This avoids the pre-intervention divergence that limited the previous CPU/GPU comparison.

On holds the accepted intention while common local planning continues around the
obstacle. The camera at 36/46 s shows occlusion; a new current-image target proposal
is accepted at 49 s, superseding the lease before its 56 s deadline. Sampled 56 s RGB
clearly shows the red tower again. The subsequent approach reaches the arrival radius
and the existing monitor declares STOP. No target truth is supplied to control.

One lease activates at 36 s from original source time 33.95 s. It authorizes 260
control ticks, including 220 using evidence older than the ordinary 4 s limit.
Original source IDs/sequences/times and the nonrenewing deadline are retained and
checked; fresh geometry supplies replanning. The switch jointly controls target
retention and deferral of LOST yaw. This pair does not isolate those two effects.

## Failure exposed by the longer budget

Off keeps exploring after the target disappears. Its actual later camera is empty
sky/ground. The first geofence rejection occurs at 124 s; 52 proposals are rejected
through 175 s. The final proposed point is 62.6 m from home, beyond the 60 m geofence.
The vehicle itself remains inside the fence and comes to rest.

The actual policy prompt includes that rejection reason and a list of rejected
image points, explicitly requesting a different proposal. Some alternatives were
tried earlier, but the final 45 s have nearly identical position, no turning, and
46 same-kind proposals with goals within 0.5 m. That meets the predeclared diagnostic
stop rule. This is evidence that the existing feedback failed to produce useful
recovery in this state. It does not prove recovery at 176–240 s was impossible.

Keep this failed trace. Before changing rejection recovery, reproduce its blank-camera
state and inspect whether the permitted action interface and available context can
express a useful return or reorientation. Do not silently modify this baseline to
improve the comparison, or add an oracle route.

## Validation and limitations

- Full replay: 3,501 off poses and 1,425 on poses match exactly, with zero missing
  source frames. All 264 off and 108 on captured input images, including boundary
  cancellations, match the corresponding replay source pixels.
- Seventeen browser seeks and two playback checks pass with no JavaScript errors.
  Actual camera/map/observer views, occlusion and reacquisition images, and the final
  success/failure states were inspected. The off outcome is labeled a diagnostic stop.
- Five preflight tests validate matching configurations and prevent the repetition
  rule from stopping a moving detour, active turn, changed-goal search or short pause.
- All raw counters are preserved. The 557/350 speed-limit counts have maximum measured
  excess 2.22e-16 m/s. One off neutral zero-command hold retains a 4.05 s age but no
  source decision; it is checked separately, not mislabeled as a leased old-source action.
- Both flights use the same fully GPU-resident model (recorded size equals size_vram,
  context 8192). Off: 262 completed requests plus two cancellations; on: 107 completed
  plus one cancellation. Total 372 attempts, all local, no cloud calls or downloads.
- Flight wall times: 361.93 s off and 172.70 s on. The first off request includes model
  startup; median measured inference latency is 0.973/1.539 s. Simulated policy/monitor
  latency remains fixed at 1.0/1.2 s, so this is not a real-time performance claim.
- Fixed order off then on, one development seed, and a censored off ending: this supports
  the mechanism in this case but does not establish a general success rate or universal
  causal effect. Previous CPU results are historical context, not a matched timing baseline.

Raw manifests/results/events, model requests and images, source snapshots, residency
records and audits are retained. `COMPARISON.json` documents the shared prefix;
`MECHANISM.json` records the first replacement, reacquisition and geofence evidence.
The initial report audit incorrectly assumed every old-age control had an owner;
that audit-only assumption was corrected after verifying the single source-less command
was an all-zero hold. No production or flight changes were made between variants.

Dedicated inference was unloaded and stopped after both flights. Shared 11434 and
Valley were not modified. Debugger 8766 remains available. No third flight launched.

## Next experiment

Keep the commitment-on implementation frozen and repeat the matched pair on additional
development seeds with the same 240 s budget. Separately retain the geofence trace as
a saved-state recovery test; do not change recovery while measuring this ablation.
D-121 remains a named architecture extension, not a change attributed to native OnFly.

[Compare the flights from the shared approach](http://127.0.0.1:8766/commitment_240_comparison.html#run=c5_commitment_on_240_20260916_s1061&t=35).
