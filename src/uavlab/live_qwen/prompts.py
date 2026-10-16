"""Role inputs use camera/state and model history, never environment scoring truth."""

import base64
import io
import json
import math

from uavlab.core.frame_store import global_store
from uavlab.interfaces import InferenceRequest
from uavlab.plugins.reasoning.shared_qwen_pilot import MONITOR, PLANNER, remaining_fru

DIRECTION = '''Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[forward_m,right_m,up_m,clockwise_degrees],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: '''


def image_text(obs):
    if obs.rgb is None:
        raise ValueError("current camera frame required")
    image = global_store().get(obs.rgb.uri)
    if image is None:
        raise ValueError("camera frame no longer available")
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def role_request(state, role, obs):
    context = dict(mission=state.mission.instruction, plan=state.plan,
                   feedback=state.feedback, completed=state.completed,
                   remaining=state.goal.error(obs) if state.goal else None,
                   speed_mps=obs.velocity.norm(), event=state.monitor_reason,
                   local_goal_terminal=state.goal.terminal if state.goal else None)
    if role == "pilot":
        context = dict(instruction=state.plan["objective"], box=None,
                       state=[*remaining_fru(obs.position, state.origin.position,
                                            state.origin.yaw_rad, obs.yaw_rad)[:3],
                              -math.degrees(state.yaw_total)],
                       remaining=state.goal.error(obs))
        prompt = json.dumps(context)
    else:
        prefix = {"planner": PLANNER, "direction": DIRECTION, "monitor": MONITOR}[role]
        prompt = prefix + json.dumps(context)
    images = () if role == "planner" else (image_text(obs),)
    return InferenceRequest(model_id=state.settings["model_id"], role=role,
                            prompt_hash=f"d135:{role}:v1", prompt=prompt,
                            images=images, image_count=len(images), observation_seq=obs.seq)
