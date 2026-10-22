"""H5 (D-174): a geometric "openings" perception primitive from the drone's own range fan.

The 4B VLM cannot ground wall openings (D-173: "left opening obscured / not visible", then
eight search turns without a box). The range fan the planner already uses (24 horizontal rays)
measures them directly: a run of long rays between two short "wall" rays is a gap; a run of long
rays next to a wall on one side only is an open wall end. This module turns that into semantic
facts (side, bearing, width, distance), handed to the condition check as measured text and used
by pass steps to aim through the named gap. Only onboard range evidence; never evaluator truth.
"""

import math

from uavlab.contracts import Vec3

FRONT_RAD = math.radians(90)
WALL_MAX_M = 20.0  # a ray shorter than this hits a surface (the fan reaches 25 m)
GAP_MARGIN_M = 4.0  # a gap ray reaches at least this much beyond the flanking wall
SIDE_DEG = 10.0  # within +/-10 deg of straight ahead counts as "ahead"
BOTH_FLANKS = 2
MIN_RAYS = 3


def side_of(bearing_deg):
    if abs(bearing_deg) <= SIDE_DEG:
        return "ahead"
    return "left" if bearing_deg > 0 else "right"


def front_rays(obs):
    rays = sorted(zip(obs.ray_bearings_rad, obs.range_rays, strict=True))
    return [(b, r) for b, r in rays if abs(b) <= FRONT_RAD]


def runs(rays, wall):
    """Maximal runs of consecutive non-wall rays, with the wall ranges that flank each run."""
    found, current = [], []
    for index, (bearing, distance) in enumerate(rays):
        if index in wall:
            if current:
                found.append(current)
            current = []
        else:
            current.append((index, bearing, distance))
    if current:
        found.append(current)
    return found


def describe(run, rays, wall):
    first, last = run[0][0], run[-1][0]
    flanks = [rays[i][1] for i in (first - 1, last + 1) if i in wall]
    bearing = sum(b for _, b, _ in run) / len(run)
    distance = min(flanks) if flanks else None
    step = abs(rays[1][0] - rays[0][0]) if len(rays) > 1 else 0.0
    width = None if distance is None else round(distance * step * (len(run) + 1), 1)
    kind = "opening" if len(flanks) == BOTH_FLANKS else "open_side"
    return dict(kind=kind, side=side_of(math.degrees(bearing)),
                bearing_deg=round(math.degrees(bearing), 1),
                distance_m=None if distance is None else round(distance, 1), width_m=width)


def find_openings(obs):
    """Gaps and open wall ends ahead of the drone, from the range fan only."""
    rays = front_rays(obs)
    if len(rays) < MIN_RAYS:
        return []
    wall = {i for i, (_, r) in enumerate(rays) if r < WALL_MAX_M}
    if not wall:
        return []
    result = []
    for run in runs(rays, wall):
        flank = [rays[i][1] for i in (run[0][0] - 1, run[-1][0] + 1) if i in wall]
        if flank and min(d for _, _, d in run) >= min(flank) + GAP_MARGIN_M:
            result.append(describe(run, rays, wall))
    return result


def range_facts(obs):
    """Measured text facts for the condition check."""
    found = find_openings(obs)
    sides_with_wall = sorted({side_of(math.degrees(b)) for b, r in front_rays(obs)
                              if r < WALL_MAX_M})
    open_sides = {o["side"] for o in found if o["kind"] == "opening"}
    return dict(measured_openings=found,
                walled_sides_without_opening=[s for s in sides_with_wall if s not in open_sides])


def named_opening(found, text):
    """The opening a step's object names ("left gap", "right opening"), else the widest one."""
    words = text.lower()
    candidates = [o for o in found if o["kind"] == "opening"]
    for side in ("left", "right"):
        if side in words:
            candidates = [o for o in candidates if o["side"] == side]
            break
    if not candidates:
        return None
    return max(candidates, key=lambda o: o["width_m"] or 0.0)


def through_point(opening, obs, beyond_m):
    """A point beyond the opening along its bearing, at the drone's altitude."""
    heading = obs.yaw_rad + math.radians(opening["bearing_deg"])
    reach = opening["distance_m"] + beyond_m
    return (Vec3(x=obs.position.x + reach * math.cos(heading),
                 y=obs.position.y + reach * math.sin(heading), z=obs.position.z), heading)
