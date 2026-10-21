# D-164 diagnostic (pre-planner), seed 1060 - stopped by design

The first paper-matrix pass ran C0, C1 and most of C2 on seed 1060. It was then stopped, because
the C0 ceiling failed (3/12) for flight-stack reasons (protocol: stop if C0 fails). These runs are
diagnostics, not results.

| Arch | Pass | Tasks passed |
|---|---|---|
| C0 oracle | 3/12 | known_goal, visible_target, overturned_vehicle |
| C1 skills | 2/12 | known_goal, visible_target |
| C2 VLM point (partial, 10 tasks) | 1/10 | visible_target |

Causes of the C0 failures:
- **No path planner in the live runtime.** The pilot flew the straight-line error and the shield
  halted it about 1.8 m from the first obstacle. Obstacle tasks ended 8-10 m short at timeout.
- **turn_search.** The oracle arrived (1.12 m) without facing the target; the task requires it
  visible.
- **approach_hover.** The oracle stopped at once, with no 2 s hold.
- **ordered_visit / follow_target.** The single-final-goal oracle has no sequence and no tracking
  (known, as in the harness C0).

Fixed in D-165. The run was stopped before C3, because later architectures would have loaded the
new code and config from disk.
