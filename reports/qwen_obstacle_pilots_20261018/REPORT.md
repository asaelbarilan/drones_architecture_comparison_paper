# D-156 obstacle tasks: can the VLA pilot avoid what the classical one cannot? (2026-10-18)

Same setup as D-155 (only the pilot differs; shield never steers, only slows
and hard-stops 1 m short). Three new tasks in `capability_grid3d`
(`OBSTACLE_SCENARIOS`), each the visible-pillar task (pillar 12 m ahead, stop
within 2 m, 60 s, seed 1061) plus obstacles; instruction adds "avoiding the
obstacles on the way".

- obstacle_post: 5 m tall post at (6, 0.7), straight path passes 0.4 m from it.
- obstacle_slalom: posts at (4.5, -0.7) and (8.5, 0.7).
- obstacle_low_wall: wall at x = 6, top 3.3 m.

Harness check (`scripts/diagnostics/check_obstacle_scenes.py`,
`scene_checks/`): depth at the grounding pixel (centre of the visible red
region) reads the pillar (12.2 m) in all three, so grounding is unaffected;
the leg the runtime issues comes within the 0.4 m drone radius of a post in
post and slalom. low_wall turned out NOT to block: grounding aims at the
visible pillar part above the wall, and that leg clears it by 0.72 m. It is
kept as a control both pilots should pass.

| Task | VLA | Classical |
|---|---|---|
| obstacle_post | fail 8.24 m; max sideways 0.20 m; stalled at x 3.8 | fail 8.15 m; max sideways 0.29 m; stalled at x 3.9 |
| obstacle_slalom | fail 9.47 m; max sideways 0.05 m | fail 9.54 m; max sideways 0.23 m |
| obstacle_low_wall (control) | fail 8.35 m; stayed at z 3.0 although the goal was z 5.0; stalled at wall | fail 2.14 m; flew over (z 4.98), stopped 1.05 m from pillar horizontally but 1.86 m above its 3 m reference |

No collisions. Shield interventions: VLA 6/6/6, classical 7/7/0.

## What this shows

- The VLA shows no avoidance: it flies straight at a visible post (0.05-0.20 m
  sideways) exactly like the blind controller, and both end stalled by the
  shield in front of it.
- The VLA also ignores the vertical part of its goal: with 2 m of climb
  requested it held 3.0 m and stalled at a wall the commanded path clears.
- Classical failed the control only by 0.14 m, from the known aim-point climb
  (grounding aims at the visible box centre, above the pillar's 3 m
  reference, D-152), not from piloting.
- Combined with D-155: on this testbed there is still no task where the
  learned pilot does better than a straight-line controller.

## Limits

One seed, three hand-built scenes, simple renderer, shield-triggered monitor
replans after the first stall (same for both). The VLA was trained on
UAV-Flow imitation flights, which may contain little obstacle avoidance.
