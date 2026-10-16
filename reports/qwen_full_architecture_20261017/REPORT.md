# D-143: full shared-Qwen architecture experiment

2026-10-17. User authorized a local whole-architecture experiment after D142.
**Result: both missions failed the end-to-end completion criterion.** The pilot
moved and reached configured arrival tolerances, but monitor/planner coordination
prevented correct mission completion. This is not evidence that the full system
works, despite successful inference acceleration and safe action execution.

## Experiment

One shared Qwen base, real planner/direction/monitor and trained VLA pilot,
persistent goals, asynchronous worker, streaming action buffer,20Hz control and
collision shield. D142 ExperimentalBackend injected into the existing fly()
runner; production defaults unchanged. No scripted model replies or task-answer
injection. Evaluator-only expected_delta values never enter model prompts.

Two original missions/seeds: forward2m (1061), right turn30degrees (1062),60s cap
each, original0.5m/5degree arrival tolerances,0.2m/s settled speed,1.5s pilot
freshness. Rendered open grid3d; **not AirSim**, no physical drone. The scene has
almost no visual landmarks. This exercises the integrated control/role loop,
not visual grounding, object detection or general cognitive mission capability.
No YOLO/OWL calls are part of this selected architecture experiment.

## Observed behavior

| Task | Behavior | Final result |
|---|---|---|
| Forward2m | Reached about1.57m, within0.5m arrival tolerance; monitor incorrectly reported no forward progress. Planner changed objective; direction authorized the episode start as a new terminal goal. Drone returned to about0.47m forward and repeatedly replanned. | Failed; endpoint error1.527m;32 actions executed. |
| Right30degrees | Turned about25.024degrees, within5degree arrival tolerance, with negligible translation. Monitor demanded a visual landmark to confirm a numeric turn and repeatedly held/replanned. | Failed completion; heading error4.976degrees, position error0.00483m;10 actions executed. |

The turn's25degree stop is consistent with the existing tolerance, not a new
precision failure. Both physically settled, but neither received valid mission
completion approval (stopped=false). No collision/out-of-bounds event; all42
consumed actions were within freshness/command expiry. Control timing passed:
forward max gap95.5ms, turn60.6ms, below existing150ms limit. About19.6Hz average.

At the first forward monitor call the input said event=arrival, remaining
forward0.479m, speed0.179m/s. It replied “No forward movement detected”. Initial
direction target[2,0,0,0] was correct; after the monitor's hold, subsequent direction
targets became[0,0,0,0]. The runner accepted that mission-changing goal. The first
turn monitor input had remaining heading4.976degrees and speed0.0079m/s; its
reply required a visible orientation cue. These exact prompts/replies are in
real_v1/*/events.jsonl and verification_local.json.

The contract mismatch is visible in the code: monitor instructions require
visible accomplishment for every mission, but numeric pose arrival should be
judged from measured pose/tolerances. Monitor gets instantaneous remaining error
and speed, without explicit tolerance values or a measured progress history.
Replanning then allows a numeric mission target to drift. These are the next
issues to fix and test; no weight update or reward adjustment was performed.

## Timing and qualifications

| Task | First complete action produced, median / max | Received by control loop, median / max |
|---|---|---|
| Forward (12 pilot requests) |200.8 /767.2ms|206.0 /814.1ms|
| Turn (4 pilot requests) |207.4 /796.3ms|253.5 /829.1ms|

Unlike D142's2ms diagnostic consumer, this experiment retains the20Hz control
loop. New request shapes can capture graphs lazily; the larger first-call spikes
were not independently profiled here, so do not attribute all delay to capture.
There is no guaranteed200ms simulator result. The original preflight gate passed
for both tasks; two startup full-chunk equivalence checks passed before readiness.
All four roles actually ran: forward7 planner/6 direction/12 pilot/6 monitor;
turn7 planner/6 direction/4 pilot/6 monitor. Replanning overhead dominates the
later portion of both missions even though no further useful movement occurs.

## Evidence and next action

- real_v1/config.json freezes unchanged mission/tolerance/freshness settings.
- source_hashes.json identifies runner and experimental backend sources.
- raw_events.zip preserves both original JSONL logs (excluded by the repository
  log ignore rule); raw_events_manifest.json records their sizes/SHA256. Extract
  into real_v1 to restore the auditor's forward/ and turn/ event paths.
- startup_equality.json, result.json, per-task events/images and
  verification_local.json preserve the original experiment.
- architecture_results.png shows actual episode-relative forward/altitude,
  heading and role timelines; shaded regions show numeric acceptance bands.
-18 existing goal/control/full-runtime tests pass; both new launcher/auditor
  pass function-size/complexity limits and Ruff. Raw events were not rewritten.
- GPU process exited; independently observed12MiB GPU memory,0% utilization.
  No AWS, retraining, model-file change or installed-package change.

Recommended next experiment: preserve the numeric mission target across replans,
provide explicit pose/tolerance/progress evidence to the monitor, and separate
numeric completion from visual-object confirmation. Test these contracts locally
before repeating these exact two missions. Do not generalize a future numeric
pass to AirSim or arbitrary visual/cognitive tasks. No additional flights run
after this failure; production architecture remains unchanged.
