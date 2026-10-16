# D-144: four easier tasks and component audit

2026-10-17. User approved hold, forward1m, right15degrees and move-then-turn,
auditing the planner, direction, pilot, monitor and trajectory separately.
**Physical hold/simple-motion behavior passed its fixed tolerances;0/4 tasks
passed full completion.** The two-stage task also failed its sequencing contract.
No policy, prompt, scheduler or acceptance-rule repair was mixed into this test.

## Fixed method

Same real shared-Qwen architecture, D142 experimental pilot, rendered open grid3d,
20Hz control,1.5s action freshness,0.5m/5degree arrival tolerance,0.2m/s settled
speed. Four seeds1071–1074,60s per mission,480s whole-process watchdog. Frozen
config/criteria in real_v1/config.json and configs/experiments/qwen_easy_components.json.
Hold additionally required displacement<=0.1m, drift<=1degree, zero executed
actions. Two-stage required movement arrival before rotation outside5degrees
and an explicit intermediate-goal advancement. All tasks require acknowledged
completion, fresh actions, passing control timing and no collision/OOB.
Criteria were saved before model launch, not adjusted to observed outcomes.
Expected poses are evaluator-only and never supplied as model answers.

## Results

| Task | Actual motion | Completion / component result |
|---|---|---|
| Hold | Zero displacement, zero heading drift, no pilot call or executed action. | Physical hold passes. Monitor says hold instead of stop; scheduler treats hold as replan. Never acknowledges completion. |
| Forward1m | About0.586m forward; endpoint error0.414m, heading error0.165deg. | Inside the existing0.5m tolerance; initial plan/direction correct. Monitor falsely says no movement and repeatedly replans. |
| Right15deg | Turns10.302deg; heading error4.698deg, position error0.004m. | Inside the existing5deg tolerance; initial numeric direction correct. Monitor demands a visual cue instead of accepting measured heading. |
| Move1m, then right15deg | Moves before significant turn, but no intermediate-goal advance. Final position error0.053m, heading error10.093deg. | Ordered displacement happened physically, but structured stage progression never occurred. Combined terminal target, then dropped turn requirement during replanning. Fails sequence and final heading. |

The broad pre-existing tolerances explain0.586m/10.302deg; these are not exact
1m/15deg execution claims. Holding does not test VLA movement because the pilot
was correctly not called. All tasks physically settled, but stopped=false means
mission completion was never acknowledged, not that the vehicle kept moving.

## Component findings

| Component | Supported conclusion |
|---|---|
| Planner | Initial simple-task objectives are sensible. Compound instruction stays prose, not ordered executable stages. After monitor feedback it omits the turn. Not reliable for multistep mission preservation. |
| Direction | Initial simple numeric targets are correct. Compound first response is invalid JSON and correctly rejected; retry merges both stages into terminal target[1,0,0,15]. Later targets[1,0,0,0] silently lose turn. |
| VLA pilot | Simple motion reaches the accepted region with fresh actions. Compound sequence is not proof of independent staged reasoning; no structured stage transition occurred. |
| Monitor | Main repeated failure. Treats featureless imagery as absence of progress, demands visual proof for numeric goals, and confuses successful hold behavior with hold status that triggers replanning. |
| Scheduler/controller | Nonblocking control and expiry enforcement work in these runs. Goal validation does not preserve the original compound mission; hold and replan responses both restart planning. |
| Collision shield / visual grounding | No collisions in an obstacle-free scene. Obstacle avoidance, object identity, grounding and general cognitive competence are not established. YOLO/OWL were not used. |

There is one recovered JSON contract failure in the compound task; no fatal
worker or graph-capacity failure. Direction first emitted named labels inside
an array, which is invalid JSON. The retry was schema-valid but semantically
collapsed the sequence. Parsing success alone is therefore insufficient.

20 actions executed (0/4/4/12), all fresh; zero collisions/OOB. Max control gaps
97.3/60.0/67.2/61.5ms pass the fixed150ms threshold. First-action produced medians
forward201.7ms, turn205.5ms, compound208.0ms (2/2/5 requests); delivered medians
228.8/231.0/254.1ms. Compound max produced817.3ms/delivered867.0ms; no hard200ms
claim. Existing startup qualification passed per task, and two full-chunk startup
equality checks passed. Repeated cognition after arrival accounts for most later
runtime. No planner/monitor speed improvement was attempted here.

## Next action

Repair the contracts before another mission suite:

1. Distinguish physical hold, safety pause, replan and completed. Provide monitor
   explicit numeric tolerances and measured progress; visual proof applies only
   when the task actually requires visual identification.
2. Represent ordered steps explicitly, keep the immutable mission requirements,
   and require intermediate completion before authorizing the next stage.
3. Validate direction output against the current authorized step, rejecting both
   invalid JSON and schema-valid goals that drop requirements.

These findings do not justify retraining the VLA or switching model weights.
The present test is an audit, not a claim those repairs are implemented.

## Evidence

real_v1/result.json, component_audit.json, verification_local.json,
startup_equality.json and source_hashes.json; per-task saved input images;
architecture_results.png (actual paths, heading and role timelines). Plot heading
wraparound was corrected in the auditor; no raw events changed. Shaded plot bands
show runtime0.5m/5deg tolerance; the stricter hold audit is recorded separately.
Original JSONL events are local and also archived in raw_events.zip with SHA256
manifest because standalone logs are ignored by Git. Extract into real_v1 for
reproduction with audit_qwen_components.py and audit_qwen_full_architecture.py.

Four new independent-auditor tests pass, including wrong-order final-pose rejection,
required intermediate advancement and rejecting a leave-and-return hold. Changed
Python passes repository size/complexity rules and Ruff. No runtime default,
training, package install or AWS change. Local GPU worker exited; independently
observed12MiB memory and0% utilization. Not AirSim or a physical-drone experiment.
