# D-155 matched comparison: VLA pilot vs classical waypoint controller (2026-10-17)

Only the pilot changes. Planner, camera grounding, monitor (all on the same
shared Qwen3-VL-4B), scheduler, safety shield, evaluator, task criteria,
60 s limits, seed 1061 and code state (D-153 v2) are identical.

- VLA run: `reports/qwen_integration_repairs_20261017/long_waypoints_v2`
- Classical run: `classical/` (config `configs/experiments/qwen_capability_classical.json`,
  identical except `"pilot_mode": "classical"`)

Classical pilot (`src/uavlab/live_qwen/classical_pilot.py`): reads the same
pilot prompt's body-frame goal error and returns the same eight 0.1 s steps.
Straight line to the goal, 2 m/s cap, 1 m/s^2 deceleration profile, yaw at
0.8 x yaw-rate limit. No image, no learned weights. It runs inside the same
worker queue (`scripts/diagnostics/classical_pilot_backend.py`); the startup
VLA equivalence check still runs on the real VLA.

| Task | VLA | Classical |
|---|---|---|
| known_goal | PASS 0.24 m, 41.0 s, path 17.9 m | PASS 0.06 m, 16.7 s, path 11.9 m |
| visible_target | PASS 1.57 m, 33.6 s | PASS 1.58 m, 28.6 s |
| approach_hover | fail 1.81 m | fail 1.59 m |
| turn_search | fail 4.26 m (pilot creep) | PASS 1.89 m, 36.5 s |
| overturned_vehicle | fail 4.00 m | fail 3.64 m |
| conditional_gate | fail 10.97 m | fail 10.77 m |
| ordered_visit | fail 11.61 m (1 of 2 visits) | fail 11.71 m (1 of 2 visits) |
| closing_passage | fail 24.00 m (never moves) | fail 24.00 m (never moves) |
| follow_target | fail 47.64 m, path 2.7 m | fail 6.19 m, path 44.0 m |
| Total | 2/9 | 3/9 |

Zero collisions in both runs. GPU peak 5071 MiB both. Per-task metrics in
`comparison.json`.

## What this shows

- On this testbed the learned pilot adds nothing over a 30-line straight-line
  controller fed the same goal: the classical pilot passes everything the VLA
  passes, is faster and takes shorter paths, and also passes turn_search.
- The remaining six failures are the same with either pilot. They are planner
  and perception gaps (branching, routing around a closed passage, hovering
  above an object, hold-then-stop, losing the next target after a visit), not
  piloting.
- Biggest gap: follow_target. The VLA crept (2.7 m in 60 s, see D-154); the
  classical pilot followed for 44 m but did not satisfy the 4-6 m / 20 deg
  tracking window.

## Limits

- One seed per task; open obstacle-free scenes, mock velocity controller,
  rendered capability_grid3d, not AirSim.
- The scenes favour a geometric controller: the planner and grounding already
  turn the camera into a 3D goal, so the pilot never has to use the image.
  A case for the VLA needs tasks where the pilot must use vision itself
  (cluttered avoidance, no depth, moving obstacles).
- Attempts 1-2 of this run failed at startup from a bug in the comparison
  wrapper (nested `_load` enabled classical mode inside the VLA equivalence
  check); kept as `classical_try1_startup_fail`, `classical_try2_startup_fail`.
  No flights ran in those attempts.
