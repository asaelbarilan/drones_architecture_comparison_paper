"""D-188 harder planning tasks for CapabilityEnv: scenes and private, staged scoring.

The 12 original tasks saturate (basic and obstacle tasks pass almost everywhere) and only two
planning tasks discriminate. These add the designs the benchmarks use
(docs/research/EVALUATION_20261024.md): a length gradient (ordered visits of 3 and 4 objects,
LoTa-Bench / LH-VLN), a condition with a search, a revisit from memory, and a spatial
relation. Each task is a sequence of stages with per-stage credit (LH-VLN style), and some
have forbidden objects whose visit is the wrong branch. Positions vary with the seed, so seeds
are different scenes. Nothing here reaches normal observations: scoring is evaluator-only.
"""

from __future__ import annotations

import numpy as np

from uavlab.adapters.gym.deterministic_env import Landmark

PLAN_SCENARIOS = ("ordered_visit_3", "ordered_visit_4", "conditional_search", "revisit",
                  "spatial_relation")
COLOURS = dict(red=(206, 44, 44), blue=(40, 85, 220), green=(40, 160, 70),
               yellow=(225, 200, 40))
DWELL_S = 0.5
JITTER_M = 1.5
SEED_SALT = 7919


def at(x, y, z=3.0):
    return np.array([x, y, z], dtype=float)


def side(rng):
    """+1 or -1, from the seeded generator."""
    return 1 if rng.integers(2) else -1


def pillar(position, colour, target=False):
    return Landmark(position.copy(), f"{colour} pillar", is_target=target, color=COLOURS[colour])


def ordered(env, colours, rng):
    """Pillars ahead in alternating lanes, visited in the stated order; the last one is the stop."""
    points = [at(8 + 6 * i, (4 if i % 2 == 0 else -4) + rng.uniform(-JITTER_M, JITTER_M))
              for i in range(len(colours))]
    env.landmarks = [pillar(p, c, i == len(points) - 1)
                     for i, (p, c) in enumerate(zip(points, colours, strict=True))]
    return [(p, DWELL_S) for p in points[:-1]] + [(points[-1], 0.0)], []


def conditional_search(env, seed, rng):
    """Blue straight ahead on even seeds, absent on odd ones; red always behind (search)."""
    red = at(-8, 6 * side(rng))
    env.landmarks = [pillar(red, "red", seed % 2 == 1)]
    if seed % 2 == 0:
        blue = at(12, rng.uniform(-JITTER_M, JITTER_M))
        env.landmarks.append(pillar(blue, "blue", True))
        return [(blue, 0.0)], [red]  # going to red when blue is in view is the wrong branch
    return [(red, 0.0)], []


def revisit(env, rng):
    """Red, then blue, then back to red, which is out of view from the blue pillar."""
    red = at(8, 3 + rng.uniform(-JITTER_M, JITTER_M))
    blue = at(16, -3 + rng.uniform(-JITTER_M, JITTER_M))
    env.landmarks = [pillar(red, "red", True), pillar(blue, "blue")]
    return [(red, DWELL_S), (blue, DWELL_S), (red, 0.0)], []


def spatial_relation(env, rng):
    """Two red pillars; the target is the one next to the car, which side depends on the seed."""
    flip = side(rng)
    car_y = flip * 4.0
    env._car(12, car_y, False)
    beside = at(12, car_y + flip * 2.8)
    alone = at(12, -car_y)
    env.landmarks = [pillar(beside, "red", True), pillar(alone, "red")]
    return [(beside, 0.0)], [alone]


def build_plan_scene(env, seed):
    """Sets landmarks / obstacles, env.goal and the staged plan for a D-188 scenario."""
    rng = np.random.default_rng(seed + SEED_SALT)
    scenario = env.scenario
    if scenario == "ordered_visit_3":
        stages, forbidden = ordered(env, ("red", "blue", "green"), rng)
    elif scenario == "ordered_visit_4":
        stages, forbidden = ordered(env, ("red", "blue", "green", "yellow"), rng)
    elif scenario == "conditional_search":
        stages, forbidden = conditional_search(env, seed, rng)
    elif scenario == "revisit":
        stages, forbidden = revisit(env, rng)
    else:
        stages, forbidden = spatial_relation(env, rng)
    env.goal = stages[-1][0].copy()
    env.target_label = next(m.label for m in env.landmarks if m.is_target)
    env.plan_stages, env.plan_forbidden = stages, forbidden
    env.plan_done, env.plan_dwell_s, env.plan_wrong = 0, 0.0, False


def update_plan(env, position, dt, t):
    """Advance the staged plan; True when every stage is done and the drone is at the last one."""
    radius = env.goal_radius_m
    env.plan_wrong |= any(np.linalg.norm(position - f) <= radius for f in env.plan_forbidden)
    last = len(env.plan_stages) - 1
    while env.plan_done < last:
        point, dwell = env.plan_stages[env.plan_done]
        near = np.linalg.norm(position - point) <= radius
        env.plan_dwell_s = env.plan_dwell_s + dt if near else 0.0
        if env.plan_dwell_s < dwell - 1e-9:
            break
        env.plan_done += 1
        env.plan_dwell_s = 0.0
        env.task_events.append({"t": t, "kind": "stage_completed", "stage": env.plan_done})
    final = env.plan_done == last and np.linalg.norm(position - env.plan_stages[-1][0]) <= radius
    return bool(final and not env.plan_wrong)


def plan_extras(env):
    """Per-stage credit for the status (the final stage counts once it is complete)."""
    total = len(getattr(env, "plan_stages", ()))
    done = getattr(env, "plan_done", 0) + (1 if env._task_complete and total else 0)
    return dict(stages_done=float(min(done, total)), stages_total=float(total),
                wrong_object=float(getattr(env, "plan_wrong", False)))
