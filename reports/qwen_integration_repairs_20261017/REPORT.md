# D-151 integration repairs: first three capability tasks (2026-10-17)

Frozen D207 shared Qwen3-VL-4B VLA (no weight changes). Same config
`configs/experiments/qwen_capability_repair.json`, seed 1061, original task
criteria and 60 s limits as D-150. Rendered `capability_grid3d`, not AirSim.
Pass/fail is the simulator evaluator's, not the monitor's claim.

| Run | Repairs in place | known_goal | visible_target | turn_search |
|---|---|---|---|---|
| D-150 baseline | none | FAIL (planner 3-value goal) | FAIL 7.57 m | FAIL, never moved |
| first_three | world contract, search turns, LRU graph cache, 0.1 s actions | FAIL (contract) | FAIL 4.61 m | FAIL 10.23 m |
| second_three | + wrapper-tolerant coordinates, depth-bounded waypoints, search sweep | PASS 0.12 m / 25.9 s | PASS 1.95 m / 39.8 s | FAIL 1.78 m, not stopped |
| third_three | + near-object standoff fix | PASS 0.28 m / 45.3 s | PASS 1.36 m / 37.9 s | PASS 1.25 m / 58.3 s |

All runs: zero collisions, zero out-of-bounds, all actions fresh, tick gaps
<= 61 ms. third_three GPU 9 MiB at start, peak 5071 MiB of 8188 MiB.

## turn_search failure in second_three: near-object waypoint deadlock

The drone found the pillar after ~27 s of stationary search turns, reached
1.78 m from it (inside the 2 m radius) by ~51 s, then hovered without stopping
until the 60 s limit. Evaluator requires a terminal stop.

Cause: waypoint travel was `distance - NEAR_OBJECT_M` (1.5 m) floored at
0.25 m. Arrival tolerance is `position_m` = 0.5 m. At depth ranges of
1.52-1.57 m each new waypoint was 0.25 m away, so it counted as reached as soon
as it was issued; grounding refreshed and issued another. Range never fell
below 1.5 m, so the proximity check never asked the monitor to verify a stop.
visible_target passed only because one depth reading happened to come in at
1.47 m.

Fix (`src/uavlab/live_qwen/scheduler.py`): aim the waypoint at standoff
`NEAR_OBJECT_M - position_m - 0.25` = 0.75 m, so the arrival point lies inside
the near range. Regression test
`test_visual_waypoint_just_outside_near_range_is_not_reached_on_issue`;
88 live-Qwen tests pass.

## Caveats

- One seed per task; these are development screens, not benchmark scores.
- known_goal in third_three took 45 s and 21.6 m of path versus 25.9 s and
  11.9 m in second_three. Same single numeric goal (12, 0, 3) both times and no
  visual waypoints, so the standoff change is not involved. This is
  run-to-run pilot variation (overshoot and correction), still a pass.
- turn_search passed with 1.7 s to spare; the ~27 s stationary search phase
  at the start is the next limit on that task.
- The other six tasks have not been rerun with these repairs.
- No matched classical-controller comparison yet.

# D-152 remaining six tasks with D-151 repairs (2026-10-17)

Same frozen VLA, config, seed 1061, original criteria, 60 s limits. Run dir
`remaining_six`. 0/6 pass; zero collisions, zero out-of-bounds.

| Task | D-150 | D-152 | Cause from trace |
|---|---|---|---|
| approach_hover | 7.48 m | 1.21 m | Visual approach climbed 3.0 -> 4.1 m, ~1.1 m off the approach line (limit 0.35 m), so evaluator hover timer never started; monitor answered "hold" 6 times, never "stop" |
| overturned_vehicle | 11.48 m | 8.01 m | Planner split find / hover-above; no goal type for "above object at 3.2 m"; ended at z 2.39; "scene unclear" recoveries |
| conditional_gate | 12.82 m | 10.74 m | Planner turned the branch into fixed "approach the wall" step; 14 shield slow-downs (2 m clearance) |
| ordered_visit | 16.54 m | 12.53 m | First visit really completed (evaluator, t=47.8 s); 12 s left for 12.5 m to blue pillar |
| closing_passage | 24.00 m | 24.00 m | Pillar hidden behind wall; 8 in-place search sweeps never see it; no "fly through the passage" action; never moved |
| follow_target | graph-cache crash | 32.51 m | Moves now; marker reached x=50 m, drone 17.5 m; never within 4-6 m |

## Common bottleneck: stop-and-go re-grounding

Each visual waypoint (<= 3 m) ends with motion revoked while a fresh grounding
call runs (~3 s, mean 2.2-3.6 s). Stationary time (speed < 0.1 m/s):

| Task | Stationary / flight |
|---|---|
| visible_target (third_three, pass) | 20.8 / 37.9 s |
| turn_search (third_three, pass) | 39.8 / 58.2 s |
| approach_hover | 45.8 / 59.9 s (includes intended hold) |
| ordered_visit | 37.7 / 60.0 s |
| follow_target | 40.5 / 60.0 s |
| overturned_vehicle | 40.8 / 59.9 s |

Removing this wait (re-ground while still flying the current waypoint) is the
shared fix that could matter for ordered_visit, follow_target and the
passing tasks' margins. The other failures need new planner capabilities
(branch, through-passage route, above-object altitude goal, tracking,
hover-duration completion) and a fix for the altitude climb.

# D-153 long visual waypoints (2026-10-17)

Goal: cut stop-and-go. A "keep flying during the camera check" design is not
possible with the VLA alone: one shared GPU model serves every role one
request at a time, a grounding call takes ~3 s, a pilot call covers 0.8 s of
flight. Chosen instead: longer legs from measured depth, up to the existing
`max_goal_m` = 10 m (was 3 m), so fewer checks per approach.

Changes: `parse_direction(payload, max_travel_m=3)` (old pilot unchanged);
`visual_goal` and scheduler use `max_goal_m`. Run `long_waypoints`: 1/9.
Two new failure modes, both fixed for `long_waypoints_v2`:
- Overshoot: 0.75 m standoff + precise arrival put the pillar out of view
  (visible_target froze on target_lost from 23 s). Now aim at
  NEAR_OBJECT_M - 0.25 = 1.25 m, minimum leg position_m + 0.1 = 0.6 m.
- Mid-leg monitor: 12 s periodic check fired during ~14 s legs; evidence is
  stale once moving, so it always answered replan and stopped the drone.
  Periodic check now skipped on committed visual steps (stall check remains).

| Task | 3 m legs (third_three / remaining_six) | long_waypoints | long_waypoints_v2 |
|---|---|---|---|
| known_goal | PASS 0.28 m / 45.3 s | PASS 0.29 / 41.0 | PASS 0.24 / 41.0 |
| visible_target | PASS 1.36 / 37.9 | FAIL 1.16 | PASS 1.57 / 33.6 |
| approach_hover | FAIL 1.21 | FAIL 1.90 | FAIL 1.81 |
| turn_search | PASS 1.25 / 58.3 | FAIL 2.85 | FAIL 4.26 |
| overturned_vehicle | FAIL 8.01 | FAIL 4.21 | FAIL 4.00 |
| conditional_gate | FAIL 10.74 | FAIL 10.76 | FAIL 10.97 |
| ordered_visit | FAIL 12.53 | FAIL 11.70 | FAIL 11.61 |
| closing_passage | FAIL 24.00 | FAIL 24.00 | FAIL 24.00 |
| follow_target | FAIL 32.51 | FAIL 43.84 | FAIL 47.64 |
| Total | 3/9 | 1/9 | 2/9 |

Zero collisions in all runs. 91 live-Qwen tests pass. One seed each.

# D-154 pilot creep probe: the VLA pilot is brittle to its inputs

turn_search v2 failed because after the search turns the pilot, given ~10 m
remaining, output ~0.02-0.13 m forward per 8-action chunk for 35 s, while on
visible_target the same 10 m input gave 2.28 m. Offline replay of saved
frames and prompts (`heading_probe/`, `scripts/diagnostics/probe_pilot_heading.py`):

| Replay | Forward per chunk |
|---|---|
| visible prompt + visible frame | 2.28 m |
| visible prompt + search frame | 1.94 m (image is not the cause) |
| search prompt + visible frame | 0.02 m |
| search instruction, visible numbers | 0.02 m |
| visible instruction, search numbers (heading 210-221 deg) | 0.02-0.13 m |
| heading wrapped to -139 deg, or set to 0 | still 0.02-0.13 m (one 1.33) |
| visible frames with position state zeroed mid-flight | 2.28 -> 0.02 m |

Conclusion: the frozen D207 pilot flies only when instruction text and
numeric state/goal stay close to a narrow training-like pattern; small
changes flip it between flying and hovering. The 3 m-leg turn_search pass
crept the same way at first and got through on short legs. This is a VLA
property, not an integration bug, and is central to the "why a VLA vs a
classical controller" question. Not fixed.
