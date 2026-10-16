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
Copy the committed active plan.target exactly for numeric steps. Do NOT output
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

## Actual calls: hold

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
Never claim completion. No prose, no extra keys. Context: {"original_mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "feedback": "initial mission"}
```

Response: `"{\"steps\":[{\"objective\":\"Hold position and heading\",\"target\":[0,0,0,0]}]}"`

### 5: direction (observation 39)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "plan": {"objective": "Hold position and heading", "target": [0, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Hold position and heading", "target": [0, 0, 0, 0]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[0,0,0,0]}"`

### 6: monitor (observation 107)

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
the last step can complete the mission. Context: {"original_mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "active_objective": "Hold position and heading", "active_step": 0, "is_last_step": true, "numeric_target": true, "position_error_m": 0.0, "heading_error_deg": 0.0, "speed_mps": 0.0, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"stop\", \"reason\": \"Position and heading acceptable, stationary, no motion.\"}"`

## Actual calls: forward

### 11: planner (observation 1)

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
Never claim completion. No prose, no extra keys. Context: {"original_mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "feedback": "initial mission"}
```

Response: `"{\"steps\":[{\"objective\":\"Move forward 1 meter\",\"target\":[1,0,0,0]}]}"`

### 12: direction (observation 43)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "plan": {"objective": "Move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 1 meter", "target": [1, 0, 0, 0]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 13: pilot (observation 76)

```text
{"instruction": "Move forward 1 meter", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0000000000000002, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0000000000000002, 0.0, 0.0, -0.0]}`

### 14: pilot (observation 107)

```text
{"instruction": "Move forward 1 meter", "box": null, "state": [0.17122188598429658, 9.432274547867964e-05, -0.0004707329540494243, -0.07145634441778728], "remaining": [0.8287775871180494, 0.0009392864263522566, 0.0004707329540494243, 0.0714563444177873]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.8287775871180494, 0.0009392864263522566, 0.0004707329540494243, 0.0714563444177873]}`

### 15: monitor (observation 135)

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
the last step can complete the mission. Context: {"original_mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "active_objective": "Move forward 1 meter", "active_step": 0, "is_last_step": true, "numeric_target": true, "position_error_m": 0.4372316037175115, "heading_error_deg": 0.17360083250479486, "speed_mps": 0.17403790612881573, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"stop\", \"reason\": \"Position error within tolerance, stationary, mission complete\"}"`

## Actual calls: turn

### 20: planner (observation 1)

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
Never claim completion. No prose, no extra keys. Context: {"original_mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "feedback": "initial mission"}
```

Response: `"{\"steps\":[{\"objective\":\"Turn right 15 degrees from the starting heading without changing position\",\"target\":[0,0,0,15]}]}"`

### 21: direction (observation 53)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Turn right 15 degrees from the starting heading without changing position", "target": [0, 0, 0, 15]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Turn right 15 degrees from the starting heading without changing position", "target": [0, 0, 0, 15]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[0,0,0,15]}"`

### 22: pilot (observation 83)

```text
{"instruction": "Turn right 15 degrees from the starting heading without changing position", "box": null, "state": [0.0, -0.0, 0.0, -0.0], "remaining": [0.0, -0.0, 0.0, 14.999999999999996]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.0, -0.0, 0.0, 14.999999999999996]}`

### 23: pilot (observation 114)

```text
{"instruction": "Turn right 15 degrees from the starting heading without changing position", "box": null, "state": [0.002559290010190635, 0.0001495279942196841, -0.0005208163538226174, 4.210931357050325], "remaining": [-0.0025633607832893997, 3.8800412509330915e-05, 0.0005208163538226174, 10.78906864294967]}
```

Response: `{"steps_fru_m_yaw_rad": [[-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [-0.0025633607832893997, 3.8800412509330915e-05, 0.0005208163538226174, 10.78906864294967]}`

### 24: monitor (observation 131)

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
the last step can complete the mission. Context: {"original_mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "active_objective": "Turn right 15 degrees from the starting heading without changing position", "active_step": 0, "is_last_step": true, "numeric_target": true, "position_error_m": 0.0012376801098548862, "heading_error_deg": 4.629606187374389, "speed_mps": 0.006828730120447403, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"stop\", \"reason\": \"Heading error within tolerance, stationary, position acceptable\"}"`

## Actual calls: move_then_turn

### 29: planner (observation 1)

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
Never claim completion. No prose, no extra keys. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "feedback": "initial mission"}
```

Response: `"{\"steps\":[{\"objective\":\"move forward 1 meter\",\"target\":[1,0,0,0]},{\"objective\":\"turn right 15 degrees\",\"target\":[0,0,0,15]}]}"`

### 30: direction (observation 67)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 31: pilot (observation 95)

```text
{"instruction": "move forward 1 meter", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0, 0.0, 0.0, -0.0]}`

### 32: pilot (observation 126)

```text
{"instruction": "move forward 1 meter", "box": null, "state": [0.2916566904996179, 8.674301425371997e-05, -0.0011556362075482163, -0.14497181533976472], "remaining": [0.7083412615422052, 0.0017055307391083028, 0.0011556362075482163, 0.14497181533976472]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7083412615422052, 0.0017055307391083028, 0.0011556362075482163, 0.14497181533976472]}`

### 33: monitor (observation 148)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.47805642194232006, "heading_error_deg": 0.23570557178718293, "speed_mps": 0.19174257966626776, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.478m exceeds 0.5m tolerance.\"}"`

### 34: monitor (observation 233)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204369556082517, "heading_error_deg": 0.23570557178718293, "speed_mps": 3.3667391910880444e-07, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 35: monitor (observation 322)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544430236, "heading_error_deg": 0.23570557178718293, "speed_mps": 3.0949452048626534e-13, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 36: monitor (observation 409)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 3.85325113963873e-19, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 37: monitor (observation 495)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 5.582070781204355e-25, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 38: monitor (observation 580)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 9.669429090738655e-31, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 39: monitor (observation 666)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 1.3528883434888209e-36, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 40: monitor (observation 756)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 1.0560407932138304e-42, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 41: monitor (observation 843)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 1.3126995982131586e-48, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 42: monitor (observation 931)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 1.4364031888283186e-54, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 43: direction (observation 981)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0]}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Do NOT output
terminal: the scheduler owns step order and mission completion.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null}}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "persistent goal expired", "completed": [], "remaining": null, "speed_mps": 5.913760895543237e-58, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 44: monitor (observation 1052)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 8.853939295083606e-63, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.42m exceeds 0.5m tolerance.\"}"`

### 45: monitor (observation 1147)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4204368544429312, "heading_error_deg": 0.23570557178718293, "speed_mps": 3.095474601437623e-69, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"streamed actions"`
