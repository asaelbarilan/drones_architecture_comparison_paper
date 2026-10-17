# D-150: existing nine-task screen

**0/9 task passes.** Seven tasks timed out without success; two were blocked by
integration errors. This is a single development seed (1061) per existing task,
not a statistical benchmark, architecture comparison or evidence against VLAs
in general. The earlier D148 shorter pillar demo remains a valid narrow success;
it did not establish capability on this broader suite.

## What ran

All nine existing `capability_*.yaml` task configurations in `SCENARIOS`, with
their original instructions, success criteria, geometry and 60-second maximum.
The approach-hover task is the D108 ninth task, within the eight original regimes.
Tracking retains its fixed 5–20-second scoring window; extra time cannot rescue it.
Original max speed 2 m/s, altitude 0.5–7 m, geofence 45 m and clearance constraints
were bound to each mission. No task criteria, prompts, model weights or scheduler
were changed between cases. Known-goal uses the existing numeric mode; the other
eight use existing visual mode. The original generic runtime proximity and
waypoint rules remain unchanged, including their limitations on non-approach tasks.

One persistent shared NF4 Qwen3-VL-4B owner, D207 step8000 action adapter and D148
event-driven runtime. Each mission resets environment/scheduler memory; the GPU
model and bounded graph caches persist across missions. Existing startup equality
and per-task nonexecuting latency probes run before flight. RGB-D and odometry
are policy inputs. Hidden goal, branch, visit and tracking truth only enter the
saved evaluator artifacts and independent final score.

The first sandbox launch stalled before model loading or flights and was stopped.
The actual nine-task run is entirely under `run/`, launched once with local
process permissions and a 1200-second watchdog. No flight retries, AWS, training,
policy repairs, publication or remote pushes occurred.

## Results

| Existing task | Outcome | Final target distance | Executed action packets | Observed failure |
|---|---|---:|---:|---|
| Known coordinates | Integration failure | 12.00 m | 0 | Planner returned `[12,0,3]` three times; runtime requires a four-channel pose. Never flew. |
| Visible red pillar | Timeout | 7.57 m | 57 | Approached about 4.43 m of the original 12 m separation; never arrived or stopped. |
| Approach and hover | Timeout | 7.48 m | 50 | Never reached the 0.75–1.25 m zone; zero qualifying hover streak. |
| Out-of-view search | Timeout | 11.31 m | 0 | Repeated absent grounding; recovery refreshed the view but never performed a search turn. |
| Overturned vehicle | Timeout | 11.48 m | 68 | Grounding selected a vehicle region, but movement/replanning never reached the hover point. |
| Conditional opening | Timeout | 12.82 m | 56 | Planner flattened the conditional into approach-wall steps; no opening crossed. |
| Red then blue | Timeout | 16.54 m to final blue | 68 | Order was represented, but the first red visit was never achieved; 0/1 required subgoals. |
| Closing passage | Timeout | 24.00 m | 0 | Target reported absent; no motion or alternate route after closure. |
| Moving marker | Integration failure | 18.94 m at abort | 0 | Three `Bounded graph cache exhausted` errors; aborted at 15.63 s. Tracking behavior not qualified. |

Distances are diagnostic, not substituted task criteria. Every `task_pass` uses
the actual environment task gate plus the original explicit-stop requirement.
No monitor-issued terminal stop was accepted on any task. Failure-free control
does not make a task successful.

All 299 consumed action packets met freshness checks; zero collisions and zero
out-of-bounds events. Tick timing passed on every case (worst gap about 63 ms).
These are execution/safety observations, not evidence of successful navigation.

## What this exposes

1. **Task-to-runtime contract gaps.** World-coordinate instructions produced a
   three-coordinate planner answer, rejected rather than silently converted into
   the runtime's relative position plus heading representation. This is not a
   learned pilot navigation failure.
2. **Limited live autonomy.** Refreshing an unchanged camera view cannot search
   behind the drone. Fixed approach steps do not implement branching, obstacle
   recovery, or continuous following. Keeping the original text in memory is
   insufficient when the executable plan does not preserve its semantics.
3. **Weak mission-scale progress.** The longer visible target was correctly
   approached but remained far away after 60 seconds. Tiny local waypoints,
   actual pilot motions and cognition pauses need separate attribution before
   blaming model training. No longer horizon was granted to make this pass.
4. **Persistent runtime cache limit.** The tracking error is from the decoder
   graph cache's eight-entry cap (`MAX_GRAPHS=8`), keyed by input shape and cache
   addresses—not the 256-token KV capacity check, which has a different error.
   It occurred late in the shared nine-mission session. An isolated tracking
   run was not performed, so do not attribute this result solely to following
   ability or instruction length.

The current implementation is not ready for claims of general cognitive drone
autonomy. This screen also does not answer whether VLA control outperforms a
classical waypoint controller: that requires a matched controller comparison
with identical perception, goals, timing and information access. Do not treat
historical simulator-clock architecture runs as matched to this wall-paced run.

No repairs are bundled into this screen. A subsequent repair should first address
the schema/cache errors and executable search/conditional semantics, then rerun
the same tasks and criteria. More training is not justified by these results alone.

## Evidence and reproducibility

- `paths.png`: all nine actual top-down paths; goal/obstacle overlays are evaluator-only.
- `initial_views.png`: unannotated camera inputs for all nine tasks.
- `run/result.json`: all nine independent task scores and full environment statuses.
- `run/<task>/decisions.json`: actual model plans, grounding, monitor and recovery outputs.
- `run/<task>/initial_camera.png`, `final_camera.png` and input images: recorded frames.
- `raw_evidence.zip` and `raw_manifest.json`: raw role/control events, exact encoded
  prompts and sampled GPU telemetry, with per-file SHA256 checksums.
- `run/config.json`, `resolved_tasks.json`, `prompt_templates.json`, `source_hashes.json`.
- `verification.json`: nine results, zero passes, source hashes unchanged, both
  startup action-equivalence cases passed, GPU unloaded to 12 MiB after exit.
- `validation.json`: 91 CPU runtime/scoring tests passed; three added Python files
  also passed repository size/complexity checks and Ruff. CPU tests establish
  contract behavior, not successful model performance.

Run from the repository root with `PYTHONPATH=src;scripts/diagnostics`:

```powershell
D:/drone_vla_pilot/venv_qwen/Scripts/python.exe scripts/diagnostics/run_qwen_capability_suite.py --out reports/NEW_NINE_TASK_RUN/run --seed 1061
python scripts/diagnostics/report_qwen_capability_suite.py reports/NEW_NINE_TASK_RUN/run
```

This execution used the repository's rendered `capability_grid3d`, **not AirSim**.
