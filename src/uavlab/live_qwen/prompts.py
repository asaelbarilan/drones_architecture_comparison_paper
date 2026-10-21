"""Role inputs use camera/state and model history, never environment scoring truth."""

import base64
import io
import json
import math

from uavlab.core.frame_store import global_store
from uavlab.interfaces import InferenceRequest
from uavlab.plugins.reasoning.shared_qwen_pilot import remaining_fru

from .grounding import GROUNDING, VISUAL_PLANNER
from .planner_memory import RECOVERY, planner_context
from .skills import SKILL, skill_context
from .skills import active as skills_active
from .visual_progress import VISUAL_MONITOR, visual_context
from .world_contract import world_target

PLANNER = '''Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Return at least one step, including for holding still. Preserve EVERY requirement.
Include ONLY movements requested by the mission, never an invented movement.
For numeric steps target is the CHANGE during THAT STEP:
[forward_m,right_m,up_m,clockwise_degrees], with position axes of episode start.
Exception: an explicit world ENU coordinate uses target={"world_enu":[x,y,z]}.
Copy its three absolute coordinates exactly; retain initial heading unless requested otherwise.
The scheduler accumulates these changes into persistent absolute targets.
For turn steps position changes are zero; do NOT repeat earlier displacement.
Separate sequential movements ONLY IF the mission explicitly requests them.
A turn-only mission is ONE step, with zero position offsets.
A hold-only mission is ONE step, objective Hold position and heading, zero offsets.
An explicitly requested move followed by a turn uses separate ordered steps.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: '''

MONITOR = '''Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
reason must be at most 15 words. One line, no prose outside JSON.
Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
Measured errors are distances TO the target, NOT positions travelled. Never
subtract an error from a target or reinterpret an error as a position.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: '''

DIRECTION = '''Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy authorized_target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For authorized_target={"world_enu":[x,y,z]} use kind="world", copy target exactly.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: '''


def image_text(obs):
    if obs.rgb is None:
        raise ValueError("current camera frame required")
    image = global_store().get(obs.rgb.uri)
    if image is None:
        raise ValueError("camera frame no longer available")
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def monitor_context(state, obs):
    if state.settings.get("goal_mode") == "visual":
        return visual_context(state, obs)
    return dict(original_mission=state.mission.instruction,
                active_objective=state.plan["objective"], active_step=state.step_index,
                is_last_step=state.step_index == len(state.steps)-1,
                numeric_target=isinstance(state.plan["target"], list)
                or world_target(state.plan["target"]),
                position_error_m=obs.position.distance_to(state.goal.position),
                heading_error_deg=abs(state.goal.error(obs)[-1]),
                speed_mps=obs.velocity.norm(),
                position_and_heading_acceptable=state.goal.arrived(obs, state.settings),
                stationary=obs.velocity.norm() <= state.settings["stopped_mps"],
                tolerances={k: state.settings[k] for k in
                            ("position_m", "heading_deg", "stopped_mps")})


def role_request(state, role, obs):
    if role == "pilot":
        context = dict(instruction=state.plan["objective"], box=None,
                       state=[*remaining_fru(obs.position, state.origin.position,
                                            state.origin.yaw_rad, obs.yaw_rad)[:3],
                              -math.degrees(state.yaw_total)],
                       remaining=state.goal.error(obs))
        prompt = json.dumps(context)
    else:
        if role == "planner":
            context = dict(original_mission=state.mission.instruction, feedback=state.feedback)
            if state.settings.get("goal_mode") == "visual":
                context["task_contract"] = (
                    "VISUAL object task. Each target MUST be a visual-description string. "
                    "Never invent numeric movements or coordinates. Approach and stop nearby "
                    "are one visual objective, not a numeric step plus a separate stop step.")
        elif role == "monitor":
            context = monitor_context(state, obs)
        else:
            context = dict(active_objective=state.plan["objective"],
                           authorized_target=state.plan["target"],
                           numeric_target=isinstance(state.plan["target"], list)
                           or world_target(state.plan["target"]))
        prefix = {"planner": PLANNER, "direction": DIRECTION, "monitor": MONITOR}[role]
        if role == "direction" and state.settings.get("goal_mode") == "visual":
            prefix = GROUNDING
        if role == "planner" and state.settings.get("goal_mode") == "visual":
            prefix = VISUAL_PLANNER
        if role == "planner" and state.planner_event:
            prefix, context = RECOVERY, planner_context(state)
        if role == "planner" and skills_active(state):
            prefix, context = SKILL, skill_context(state, obs)
        if role == "monitor" and state.settings.get("goal_mode") == "visual":
            prefix = VISUAL_MONITOR
        prompt = prefix + json.dumps(context)
    images = () if role == "planner" else (image_text(obs),)
    return InferenceRequest(model_id=state.settings["model_id"], role=role,
                            prompt_hash=f"d148:{role}:v1", prompt=prompt,
                            images=images, image_count=len(images), observation_seq=obs.seq)
