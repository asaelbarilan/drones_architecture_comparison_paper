# D-157 VLM-side fix 1: hold altitude on visual approach legs (2026-10-18)

Problem (D-152): visual waypoints follow the camera ray to the grounding box
centre; for a tall object that centre is above its body, so the drone climbed
~1-2 m on every approach. Fix: `visual_goal` keeps the ray's horizontal aim
and holds the current altitude when `visual_altitude` is "hold" (default
"ray" keeps old behaviour; set to "hold" in the capability repair and
classical configs). Test: `test_visual_goal_altitude_mode`.

Run: `aim_height_classical/`, classical pilot (keeps VLA brittleness out of
VLM-side measurements), nine tasks, seed 1061, same criteria. Baseline: D-155
classical run.

| Task | D-155 classical | D-157 hold altitude |
|---|---|---|
| known_goal | PASS 0.06 m / 16.7 s | PASS 0.12 m / 16.7 s |
| visible_target | PASS 1.58 m / 28.6 s | PASS 1.48 m / 23.2 s |
| approach_hover | fail 1.59 m | fail 1.49 m (z 3.0, level) |
| turn_search | PASS 1.89 m / 36.5 s | PASS 1.21 m / 37.1 s |
| overturned_vehicle | fail 3.64 m | fail 0.48 m (at hover point, not stopped) |
| conditional_gate | fail 10.77 m | fail 10.67 m |
| ordered_visit | fail 11.71 m | fail 11.64 m |
| closing_passage | fail 24.00 m | fail 24.00 m |
| follow_target | fail 6.19 m | fail 9.21 m |
| Total | 3/9 | 3/9 |

Zero collisions. Same pass count; drone now flies level and ends closer.

Remaining blockers found (next fix, both "stop" decisions):
- approach_hover: holds still 1.49 m from the pillar, outside the evaluator's
  0.75-1.25 m hover window, so the hover timer never starts; monitor keeps
  answering "hold" (never "stop").
- overturned_vehicle: reaches the hover point (0.48 m) but the car is below the
  forward camera, grounding reports target lost, so the stop is never verified.

# D-158 VLM-side fix 2: deciding when a visual step is done (2026-10-18)

Three rules (`src/uavlab/live_qwen/stop_rules.py`, scheduler, `mission_plan.py`):
- Object memory: each grounding with depth stores the object's world estimate
  (pixel ray x range). If the object later leaves the forward camera while the
  drone is within the near limit horizontally of a recent (<= 15 s) estimate of
  the same target and is still, the step is complete (`object_below_completion`).
- Stated standoff and hold: `standoff_m` ("about N metres before/from it") and
  `hold_s` ("hold for N seconds") per step. First run asked the planner for
  them (prompt fields); the 4B planner omitted them, so they are now read from
  the step's own text, like explicit coordinates in `world_contract`. A stated
  standoff aims at that distance and tightens "near" to standoff + 0.25 m; a
  stated hold keeps the drone still that long, rechecks near, then finishes.
- Monitor "hold" with fresh near depth and a stationary drone counts as "stop"
  (the model uses "hold" for "stay here"; the shield handles hazards).

Runs (classical pilot, nine tasks, seed 1061):

| Task | D-157 | stop_rules (planner fields) | stop_rules_v2 (text + hold-as-stop) |
|---|---|---|---|
| known_goal | PASS | PASS 0.04 m | PASS 0.12 m / 16.9 s |
| visible_target | PASS | PASS 1.46 m | PASS 1.49 m / 23.8 s |
| approach_hover | fail 1.49 m | fail 1.47 m (planner gave no fields) | PASS 1.19 m / 33.1 s, hover streak 12.7 s |
| turn_search | PASS | PASS 1.19 m | PASS 1.18 m / 37.7 s |
| overturned_vehicle | fail 0.48 m | PASS 0.22 m / 30.2 s | PASS 0.60 m / 36.7 s |
| conditional_gate | fail | fail 10.67 m | fail 10.67 m |
| ordered_visit | fail | fail 11.65 m | fail 11.66 m |
| closing_passage | fail | fail 24.00 m | fail 24.00 m |
| follow_target | fail | fail 6.25 m | fail 9.26 m |
| Total | 3/9 | 4/9 | 5/9 |

Zero collisions. Vehicle check: memory estimate (12.45, 4.41, 1.2) is the
overturned car at (12, 4, 0.9), not the upright one at (12, -4); both plan
steps completed via object memory. Hover: standoff 1.0 and hold 2 s read from
text; evaluator hover streak 12.7 s, no contact.

Remaining four: conditional_gate (branch flattened), ordered_visit (loses the
second target after the first visit), closing_passage (no route when the
pillar is hidden), follow_target (no tracking behaviour).
