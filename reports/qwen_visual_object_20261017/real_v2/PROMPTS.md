# Exact model prompts

One shared Qwen base; pilot uses the trained adapter. Other roles disable it. No separate system message is supplied.

## planner template

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Return at least one step, including for holding still. Preserve EVERY requirement.
Include ONLY movements requested by the mission, never an invented movement.
For numeric steps target is the CHANGE during THAT STEP:
[forward_m,right_m,up_m,clockwise_degrees], with position axes of episode start.
The scheduler accumulates these changes into persistent absolute targets.
For turn steps position changes are zero; do NOT repeat earlier displacement.
Separate sequential movements ONLY IF the mission explicitly requests them.
A turn-only mission is ONE step, with zero position offsets.
A hold-only mission is ONE step, objective Hold position and heading, zero offsets.
An explicitly requested move followed by a turn uses separate ordered steps.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: 
```

## direction template

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy authorized_target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: 
```

## monitor template

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: 
```

## Pilot format

The JSON request is converted by the frozen package codec to `Current State: {state}, What action should the uav take to {instruction}?`, with the current image, assistant bounding-box prefix and `Left` progress line. The archive contains actual input token IDs and decoded strings for ALL roles, including startup and preflight calls; image-pad tokens are not image pixels.

## Actual calls: red_pillar

### 4: planner (observation 1)

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Return at least one step, including for holding still. Preserve EVERY requirement.
Include ONLY movements requested by the mission, never an invented movement.
For numeric steps target is the CHANGE during THAT STEP:
[forward_m,right_m,up_m,clockwise_degrees], with position axes of episode start.
The scheduler accumulates these changes into persistent absolute targets.
For turn steps position changes are zero; do NOT repeat earlier displacement.
Separate sequential movements ONLY IF the mission explicitly requests them.
A turn-only mission is ONE step, with zero position offsets.
A hold-only mission is ONE step, objective Hold position and heading, zero offsets.
An explicitly requested move followed by a turn uses separate ordered steps.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "feedback": "initial mission", "task_contract": "VISUAL object task. Each target MUST be a visual-description string. Never invent numeric movements or coordinates. Approach and stop nearby are one visual objective, not a numeric step plus a separate stop step."}
```

Response: `"{\n  \"steps\": [\n    {\n      \"objective\": \"Approach the red pillar\",\n      \"target\": \"Approach the red pillar\"\n    },\n    {\n      \"objective\": \"Stop nearby while keeping the red pillar visible\",\n      \"target\": \"Stop nearby while keeping the red pillar visible\"\n    }\n  ]\n}"`

### 5: direction (observation 98)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy authorized_target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\"kind\":\"visual\",\"target\":{\"u\":500,\"v\":500,\"travel_m\":1.0,\"target_visible\":false,\"box\":null}}"`

### 6: pilot (observation 152)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [0.9950041652780258, 0.0, -0.09983341664682799, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.07063350588235284, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.09101360000000003, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1113936941176471, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.11818705882352942, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.11818705882352942, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.11818705882352942, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.11818705882352942, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.11818705882352942, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151552, 151515, 151539, 151484, 151549, 151515, 151539, 151484, 151546, 151515, 151539, 151484, 151545, 151515, 151539, 151484, 151545, 151515, 151539, 151484, 151545, 151515, 151539, 151484, 151545, 151515, 151539, 151484, 151545, 151515, 151539, 151484], "remaining_supplied": [0.9950041652780258, 0.0, -0.09983341664682799, -0.0]}`

### 7: pilot (observation 183)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.06257132105429317, 0.00010522744215820529, -0.00047026931463589605, -0.0713766622247827], "remaining": [0.9324322517846448, 0.0010563577949925795, -0.09936314733219209, 0.0713766622247827]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, 0.00706895882352937, -0.0005490470588235263, -0.0009852058823529575], [0.09101360000000003, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.09101360000000003, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.0842202352941177, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.0842202352941177, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.0842202352941177, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.07063350588235284, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.07063350588235284, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151549, 151513, 151539, 151484, 151549, 151514, 151539, 151484, 151549, 151514, 151539, 151484, 151550, 151514, 151539, 151484, 151550, 151514, 151539, 151484, 151550, 151514, 151539, 151484, 151552, 151514, 151539, 151484, 151552, 151514, 151539, 151484], "remaining_supplied": [0.9324322517846448, 0.0010563577949925795, -0.09936314733219209, 0.0713766622247827]}`

### 8: pilot (observation 214)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.28613184751119014, 0.010715506817452702, -0.0018492828618721369, -0.21635263214792883], "remaining": [0.7089077263460541, -0.008038688285320839, -0.09798413378495585, 0.21635263214792883]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151516, 151539, 151483, 151542, 151516, 151539, 151483, 151542, 151516, 151539, 151483, 151542, 151516, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7089077263460541, -0.008038688285320839, -0.09798413378495585, 0.21635263214792883]}`

### 9: monitor (observation 239)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.469395265306869, "heading_error_deg": 0.009304111287832696, "speed_mps": 0.1946976360490337, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet stationary.\"\n}"`

### 10: monitor (observation 320)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.41228383831017734, "heading_error_deg": 0.009304111287832696, "speed_mps": 6.317592654164555e-07, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Red pillar visible; motion needed to approach within tolerance.\"}"`

### 11: monitor (observation 401)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.41228365357124763, "heading_error_deg": 0.009304111287832696, "speed_mps": 2.0180860386331588e-12, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Red pillar visible; approach needed despite acceptable error.\"}"`

### 12: monitor (observation 479)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 1.0361533723992205e-17, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; motion needed to approach within tolerance.\"\n}"`

### 13: monitor (observation 562)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 2.401216556161033e-23, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; motion needed to approach within tolerance.\"\n}"`

### 14: monitor (observation 646)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 4.781633040650913e-29, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Red pillar visible; motion needed to approach it.\"}"`

### 15: monitor (observation 732)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 6.959633169785028e-35, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Red pillar visible; motion needed to approach it.\"}"`

### 16: monitor (observation 817)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 1.1961149708270508e-40, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Speed too low; motion needed to approach red pillar.\"}"`

### 17: monitor (observation 900)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 2.7738965492607545e-46, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Red pillar visible; motion needed to approach it.\"}"`

### 18: monitor (observation 983)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4122836535706584, "heading_error_deg": 0.009304111287832696, "speed_mps": 6.4470297536425895e-52, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Red pillar visible; approach ongoing, not yet stopped.\"}"`

### 19: direction (observation 1029)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy authorized_target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\"kind\":\"visual\",\"target\":{\"u\":500,\"v\":500,\"travel_m\":1.0,\"target_visible\":false,\"box\":null}}"`

### 20: pilot (observation 1090)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.5942495642799149, 0.005267533990327672, -0.003159667024315027, -0.009304111287832696], "remaining": [0.9950041652780258, -5.551115123125783e-17, -0.09983341664682799, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1657406117647059, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1657406117647059, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1657406117647059, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1657406117647059, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1657406117647059, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151538, 151515, 151539, 151484, 151538, 151515, 151539, 151484, 151538, 151515, 151539, 151484, 151538, 151515, 151539, 151484, 151538, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.9950041652780258, -5.551115123125783e-17, -0.09983341664682799, -0.0]}`

### 21: pilot (observation 1121)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.9267429754008899, 0.005275726238042816, -0.004261114088361495, -0.14807437602145476], "remaining": [0.662508967315226, 0.0015424133846199395, -0.09873196958278152, 0.13877026473362206]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.00706895882352937, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151513, 151539, 151484, 151542, 151513, 151539, 151484, 151542, 151514, 151539, 151484, 151542, 151514, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.662508967315226, 0.0015424133846199395, -0.09873196958278152, 0.13877026473362206]}`

### 22: monitor (observation 1140)

```text
Assess ONLY the active step, preserving the original mission.
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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4718223687354919, "heading_error_deg": 0.21242211435972794, "speed_mps": 0.18690451456173515, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet stationary.\"\n}"`
