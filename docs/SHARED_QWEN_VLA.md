# D-132: one local Qwen base, four roles

## D-134 streaming development boundary

The new `QwenWorker` owns one Qwen model in a spawned process; its parent can
poll without waiting for generation. Four raw tokens form one complete action.
`ActionTokenStream` decodes that quartet into a JSON-compatible record immediately;
the model does not spend tokens spelling JSON. `ActionBuffer` accepts the next
indexed record while the consumer is already using the previous one.

Records carry request ID, goal version, observation sequence, original capture
timestamp, expiry, raw tokens and forward/right/up metres plus clockwise yaw
radians. A later record cannot extend the image lifetime. The consumer rechecks
expiry/goal version before taking an action. On hold/replan call both
`worker.revoke()` and `buffer.revoke()`; late replies are discarded. An empty queue
means no new motion command; the eventual controller must hold/brake safely.
Cancellation is checked between tokens, not in the middle of a running GPU kernel.

Use `WorkItem` with actual monotonic capture time, `buffer.begin(request_id,
goal_version)`, then `worker.submit(item)`. Poll for action/result/done events;
convert action events with `action_record`, append and consume from the buffer.
Admission allows one outstanding model request; scheduling priorities belong above
this boundary. The generic worker can run base language roles too; a long language
call is currently discarded after revocation, not preempted within generation.

`shared_qwen_vla_first_action_dev` requests four tokens rather than 32 because
the existing policy executes only the first action. The input remains the trained
eight-action prompt. The original and cached profiles retain eight actions.
Streaming plus action buffering is tested separately from that synchronous profile.

See [local measurements](../reports/qwen_stream_20261016/REPORT.md) and
[research recommendation](research/20261016_latency/DECISION.md). Persistent
VLM-approved goals, event priorities and actual controller/shield integration are
still required. The tests do not establish flight, target-grounding or mission
success. The rest of this document describes the earlier D-132 integration.

## Original integration

Development integration requested on 2026-10-16. The existing Ollama architecture
profiles are unchanged. This profile uses the complete private D207 step8000
package already downloaded locally, not the experimental PPO adapter.

D-133 adds a separate `shared_qwen_vla_cached_dev` profile. It reuses exact prompt
prefills per role and exact visual batches per adapter mode, with 256 MiB KV and
64 MiB visual limits. Changed prompts get fresh decoder prefill: partial-prefix
reuse changed outputs in the NF4 test and is disabled. All 15 final full-model
comparisons match fresh generated tokens and first-step logits exactly. See
[cache report](../reports/shared_qwen_cache_20261016/REPORT.md) for timings and limits.
The D-132 behavior below still describes the original uncached profile.

| Role | Weights used | Output |
|---|---|---|
| Planner | Qwen3-VL-4B base, LoRA disabled | Objective and visual target description |
| Direction | Same base, LoRA disabled | Current image point, travel distance, optional box |
| Monitor | Same base, LoRA disabled | Continue, hold, replan or stop |
| Pilot | Same base, D207 LoRA enabled | Eight action deltas; execute first and observe again |

Calls are serialized. There is one base allocation and one unmerged adapter;
generation caches are fresh for each call. No second Ollama model/server is used.
The official package supplies tokenizer, action normalization and decoder.
The pilot receives measured start-relative state and a remaining local goal,
instead of inventing its own remaining-goal prefix. Normalized boxes are refreshed
from each current image. The anchored local goal is checked before advancing it.

Actions convert trained forward/right/up and clockwise yaw into ENU and CCW yaw.
The adapter returns eight steps, but only the first is executed. These are explicit
new architecture choices, not a claim to reproduce the original VLA benchmark.
Stopping requires a monitor stop AND local position <=0.5m, heading <=5 degrees,
speed <=0.2m/s. This is not independent proof that the semantic mission succeeded.
Malformed role output produces a hold. There is no simulator-label fallback.

## D135 asynchronous runtime

The separate `uavlab.live_qwen` runtime connects persistent direction-approved
goals to streamed pilot actions and the existing controller/shield. Planning runs
at startup/replan; monitoring runs on arrival/stall/shield/periodic events. Control
does not wait on model calls. One GPU process serializes all roles; cognitive calls
hold motion while physics continues. Intermediate goals advance planning; a
monitor STOP alone cannot bypass position, heading, speed or terminal-goal checks.

See `reports/qwen_async_20261016/REPORT.md` and
`configs/experiments/qwen_async_local.json`. Scripted integration passes, but both
real-model grid3d tasks fail because actions miss the1.5s deadline. It is not yet
flight-qualified. No AirSim, grounding or general cognitive-task success claimed.
The D132 descriptions below remain historical behavior of the original profile.

## What is verified

See `reports/shared_qwen_vla_20261016/final/result.json` and `calls.jsonl`.
The probe checks four real GPU roles, one load, identical base text and next-token
logits after pilot switching, and two real-policy simulator action steps.
CPU tests additionally cover frame conversion, invalid output, stopping guards,
adapter restoration after an exception, and profile composition.

## What is not verified

The short simulator probe explicitly pauses simulation during model inference.
It tests wiring, not real-time control, routing, shield behavior, mission completion,
or AirSim dynamics. The actual architecture backend charges measured inference
time, including a cold load if not preloaded. Its normal staleness checks remain
enabled. Multi-second sequential role calls exceed the inherited 1.5-second
staleness budget; this profile is not admitted for unattended missions.

The simple grid renderer also exposes questionable grounding: a numeric forward
instruction can make the direction role invent a visual target box. A valid JSON
response is not evidence of a correct target. Before mission evaluation, validate
the point/box on visible-target camera inputs and implement an explicit hover,
fresh-observation scheduling contract. Do not silently relax timing or present
paused simulation as real-time success. No new training is needed for this wiring.

## Reproduce the local probe

From this repository in PowerShell, using the existing model environment:

```powershell
$env:PYTHONPATH='src'
$env:USE_TF='0'
$env:D132_OUTPUT='reports/shared_qwen_vla_new_probe'
& D:/drone_vla_pilot/venv_qwen/Scripts/python.exe -u scripts/probe_shared_qwen.py
```

The script refuses an existing completed output folder and has a ten-minute
process watchdog. It does not train, contact AWS, or download weights. On success
it unloads the model; a process exit also releases its GPU allocation.
The package location is configurable in `shared_qwen_vla_dev.yaml`.

PEFT adapter disabling reference:
https://huggingface.co/docs/peft/main/package_reference/peft_model
