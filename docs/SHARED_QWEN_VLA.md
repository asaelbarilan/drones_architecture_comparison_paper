# D-132: one local Qwen base, four roles

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
