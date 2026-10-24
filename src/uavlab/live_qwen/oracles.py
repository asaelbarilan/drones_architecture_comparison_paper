"""Privileged oracle swaps for capability attribution (D-185). Reference lines, never results.

One level at a time is replaced by a perfect version while the rest of the stack is unchanged
(the PRISM / StructNav method, docs/research/EVALUATION_20261024.md):
- oracle_plan: the planner's first program is the correct typed program for the mission,
  written once by hand from the public mission text (configs/experiments/oracle_programs.json);
  recovery calls still go to the model.
- oracle_grounding: a direction look returns the true box of the step's object, from the
  evaluator scene, only when the object is in view and not hidden behind a wall (the depth
  image must reach it); otherwise the model answers as usual. A hidden object is never given
  away.
The pilot oracle is a configuration (C0_VLA: the C0 goal with the VLA pilot), not code here.
"""

import json
import math

import numpy as np

from .architecture import switch
from .grounding import COORD_MAX, capture_depth

COLOURS = ("red", "blue", "green", "yellow")
PILLAR = dict(radius_m=0.5, half_height_m=1.5)
VEHICLE = dict(radius_m=1.0, half_height_m=0.6)
HIDDEN_MARGIN_M = 1.5  # the depth ray may stop this far in front of the object's centre
MIN_BOX = 8  # normalized units


def oracle_program(state):
    """The hand-written typed program for this mission, or None."""
    if (not switch(state.settings, "oracle_plan") or state.planner_event
            or switch(state.settings, "contract") != "typed"):
        return None
    program = state.settings.get("oracle_program")
    return None if program is None else json.dumps(program)


def scene_objects(env):
    """(label, position, kind) of every object in the evaluator scene, positions live."""
    objects = [(mark.label, np.asarray(mark.position, dtype=float), PILLAR)
               for mark in env.landmarks]
    for vehicle in env.debug_scene().get("vehicles", []):
        label = "overturned vehicle" if vehicle["inverted"] else "upright vehicle"
        objects.append((label, np.asarray(vehicle["position"], dtype=float), VEHICLE))
    return objects


def named_object(objects, text):
    """The object the step names: a vehicle by orientation, else the first colour mentioned."""
    words = text.lower()
    if "vehicle" in words or "car" in words:
        wanted = ("overturned" if any(w in words for w in ("overturn", "upside")) else
                  "upright")
        return next((o for o in objects if o[0].startswith(wanted)), None)
    mentioned = sorted((words.find(c), c) for c in COLOURS if c in words)
    for _, colour in mentioned:
        match = next((o for o in objects if o[0].startswith(colour)), None)
        if match is not None:
            return match
    return None


def camera_point(position, obs, pitch):
    """(forward, right, up) of a world point in the camera frame (inverse of point_to_enu)."""
    dx, dy, dz = (position[i] - v for i, v in enumerate(
        (obs.position.x, obs.position.y, obs.position.z)))
    cos_y, sin_y = math.cos(obs.yaw_rad), math.sin(obs.yaw_rad)
    forward_body = dx * cos_y + dy * sin_y
    right = dx * sin_y - dy * cos_y
    cos_p, sin_p = math.cos(-pitch), math.sin(-pitch)
    forward = forward_body * cos_p - dz * sin_p
    up = forward_body * sin_p + dz * cos_p
    return forward, right, up


def true_box(obj, obs, settings, depth):
    """The object's normalized box when it is in view and not hidden, else None."""
    _, position, size = obj
    intr = obs.intrinsics
    forward, right, up = camera_point(position, obs, settings["camera_pitch_rad"])
    if intr is None or forward <= size["radius_m"]:
        return None
    px = intr.cx + right * intr.fx / forward
    py = intr.cy - up * intr.fy / forward
    if not (0 <= px < intr.width and 0 <= py < intr.height):
        return None
    if depth is not None and depth[int(py), int(px)] < forward - HIDDEN_MARGIN_M:
        return None  # a wall is in front of it: never give a hidden object away
    half_w = max(MIN_BOX / 2, size["radius_m"] * intr.fx / forward * COORD_MAX / intr.width)
    half_h = max(MIN_BOX / 2, size["half_height_m"] * intr.fy / forward * COORD_MAX / intr.height)
    u, v = px * COORD_MAX / intr.width, py * COORD_MAX / intr.height
    box = [u - half_w, v - half_h, u + half_w, v + half_h]
    return [int(min(COORD_MAX, max(0, round(b)))) for b in box]


def oracle_look(state, obs):
    """A grounding answer from the evaluator scene, or None to let the model answer."""
    env = getattr(state, "oracle_env", None)
    if env is None or not switch(state.settings, "oracle_grounding"):
        return None
    target = (state.plan or {}).get("target")
    obj = named_object(scene_objects(env), target) if isinstance(target, str) else None
    if obj is None:
        return None  # e.g. an opening: not an object in the scene, the model looks
    box = true_box(obj, obs, state.settings, capture_depth(obs))
    return dict(target_visible=box is not None, box=box)


def privileged_answer(state, role, obs, captured, now):
    """Answer a planner / direction request from an oracle instead of the model, if on."""
    if role == "planner":
        program = oracle_program(state)
        if program is None:
            return False
        state.log("oracle_plan", now, program=program)
        state.accept_planner(program, now)
        return True
    if role != "direction":
        return False
    look = oracle_look(state, obs)
    if look is None:
        return False
    state.log("oracle_grounding", now, payload=look, source_seq=obs.seq)
    state.last_look_sim = obs.t_sim_ns
    state.pending_depth = capture_depth(obs)
    try:
        state.accept_goal(json.dumps(look), obs, captured, now)
    except (ValueError, KeyError, TypeError) as exc:
        state.failure(str(exc), now)
    finally:
        state.pending_depth = None
    return True
