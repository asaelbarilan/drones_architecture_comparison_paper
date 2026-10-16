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
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
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

### 5: direction (observation 33)

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

### 6: monitor (observation 100)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "plan": {"objective": "Hold position and heading", "target": [0, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": [-0.0, 0.0, 0.0, -0.0], "speed_mps": 0.0, "event": "arrival", "local_goal_terminal": true, "ordered_steps": [{"objective": "Hold position and heading", "target": [0, 0, 0, 0]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"The mission objective to hold position and heading is confirmed complete because position_and_heading_acceptable is true and stationary is true, with no motion detected. The system is at the target pose [0, 0, 0, 0] and meets all criteria for completion, including the final step being terminal.\"\n}"`

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

### 12: direction (observation 36)

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

### 13: pilot (observation 63)

```text
{"instruction": "Move forward 1 meter", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0000000000000002, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0000000000000002, 0.0, 0.0, -0.0]}`

### 14: pilot (observation 94)

```text
{"instruction": "Move forward 1 meter", "box": null, "state": [0.18982197872994588, 9.563307925737272e-05, -0.000521869383329765, -0.07722542325203628], "remaining": [0.8101774142561736, 0.0009963553214098753, 0.000521869383329765, 0.07722542325203628]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.8101774142561736, 0.0009963553214098753, 0.000521869383329765, 0.07722542325203628]}`

### 15: monitor (observation 120)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "plan": {"objective": "Move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": [0.4360710959966484, 0.0015149502482052976, 0.0015503786585204793, 0.1738891921781185], "speed_mps": 0.1737052122757201, "event": "arrival", "local_goal_terminal": true, "ordered_steps": [{"objective": "Move forward 1 meter", "target": [1, 0, 0, 0]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"The mission objective to move forward 1 meter has been achieved, as indicated by the feedback showing arrival at the target position. The position_and_heading_acceptable and stationary conditions are satisfied, and since this is the last step, the mission is complete.\"\n}"`

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

### 21: direction (observation 48)

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

### 22: pilot (observation 77)

```text
{"instruction": "Turn right 15 degrees from the starting heading without changing position", "box": null, "state": [0.0, -0.0, 0.0, -0.0], "remaining": [0.0, -0.0, 0.0, 14.999999999999996]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.0, -0.0, 0.0, 14.999999999999996]}`

### 23: pilot (observation 108)

```text
{"instruction": "Turn right 15 degrees from the starting heading without changing position", "box": null, "state": [0.0025633626714709197, 0.00014979731195372773, -0.0005216456271361913, 4.207089369596887], "remaining": [-0.0025674448239982623, 3.86587103202564e-05, 0.0005216456271361913, 10.792910630403107]}
```

Response: `{"steps_fru_m_yaw_rad": [[-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [-0.0025674448239982623, 3.86587103202564e-05, 0.0005216456271361913, 10.792910630403107]}`

### 24: monitor (observation 125)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Turn right 15 degrees from the starting heading without changing position", "target": [0, 0, 0, 15]}, "feedback": "initial mission", "completed": [], "remaining": [-0.00040175665479256085, 4.965384777611497e-07, 0.0011700879378220286, 4.636149518689672], "speed_mps": 0.006835046577303164, "event": "arrival", "local_goal_terminal": true, "ordered_steps": [{"objective": "Turn right 15 degrees from the starting heading without changing position", "target": [0, 0, 0, 15]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"The mission objective to turn right 15 degrees from the starting heading without changing position has been achieved, as confirmed by the measured pose matching the target [0, 0, 0, 15] within acceptable tolerances. The position_and_heading_acceptable and stationary conditions are both true, and since this is the last step, the active step is complete.\"\n}"`

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

### 30: direction (observation 64)

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

### 31: pilot (observation 92)

```text
{"instruction": "move forward 1 meter", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0, 0.0, 0.0, -0.0]}`

### 32: pilot (observation 123)

```text
{"instruction": "move forward 1 meter", "box": null, "state": [0.29142039732185726, 8.677384330120467e-05, -0.0011546999391427448, -0.14508709372925993], "remaining": [0.7085775506075039, 0.0017075234360529035, 0.0011546999391427448, 0.14508709372925993]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7085775506075039, 0.0017075234360529035, 0.0011546999391427448, 0.14508709372925993]}`

### 33: monitor (observation 145)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": [0.47792118243622816, 0.0022237485002991764, 0.0020686224693355904, 0.2358379652523434], "speed_mps": 0.1921926629451828, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"The current step is to move forward 1 meter, but the measured position [0.4779, 0.0022, 0.0021, 0.2358] indicates the robot has not yet reached the target [1, 0, 0, 0]. The position error is 0.5221 meters, which exceeds the tolerance of 0.5 meters, so the step is not complete. Additionally, the robot is not stationary, as indicated by the non-zero velocity,"`

### 34: direction (observation 327)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "Unterminated string starting at: line 3 column 13 (char 38)", "completed": [], "remaining": null, "speed_mps": 9.36896869548124e-14, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 35: monitor (observation 396)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "Unterminated string starting at: line 3 column 13 (char 38)", "completed": [], "remaining": [0.4201909085327074, 0.002111041365756349, 0.0022973685120990517, 0.2358379652523434], "speed_mps": 1.957977637284325e-18, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"The active step is to move forward 1 meter, but the current position is not yet at the target. The measured position [0.42019, 0.00211, 0.002297, 0.23584] indicates the robot is still 0.58 meters short of the 1-meter mark, and the heading is not yet aligned with the target. Therefore, motion is required to complete this step before proceeding to the next one.\"\n}"`

### 36: monitor (observation 609)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "The active step is to move forward 1 meter, but the current position is not yet at the target. The measured position [0.42019, 0.00211, 0.002297, 0.23584] indicates the robot is still 0.58 meters short of the 1-meter mark, and the heading is not yet aligned with the target. Therefore, motion is required to complete this step before proceeding to the next one.", "completed": [], "remaining": [0.4201909085327074, 0.002111041365756349, 0.0022973685120990517, 0.2358379652523434], "speed_mps": 7.08755089837765e-33, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"The measured position [0.42019, 0.00211, 0.002297, 0.23584] shows the robot is still 0.58 meters short of the 1-meter target, and the heading is not aligned with the target. The position_and_heading_acceptable flag is true, but stationary is true, which means the robot is not moving. Since the position is not yet at the target, motion is required to complete this step. The robot must move forward"`

### 37: direction (observation 796)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "Unterminated string starting at: line 3 column 13 (char 38)", "completed": [], "remaining": null, "speed_mps": 1.5752028925546104e-45, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 38: monitor (observation 866)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "Unterminated string starting at: line 3 column 13 (char 38)", "completed": [], "remaining": [0.4201909085327074, 0.002111041365756349, 0.0022973685120990517, 0.2358379652523434], "speed_mps": 2.807057436686757e-50, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"The active step is to move forward 1 meter, and the current position is within acceptable tolerance (0.42m from target, which is less than 0.5m tolerance). However, the system is not yet stationary (speed_mps is non-zero, indicating motion is still occurring). Therefore, more motion is needed to complete this step before proceeding to the next one.\"\n}"`

### 39: monitor (observation 1038)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON with exactly status and reason. Explain measured evidence in reason;
do not copy a template placeholder. Choose status using the rules below.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, "feedback": "The active step is to move forward 1 meter, and the current position is within acceptable tolerance (0.42m from target, which is less than 0.5m tolerance). However, the system is not yet stationary (speed_mps is non-zero, indicating motion is still occurring). Therefore, more motion is needed to complete this step before proceeding to the next one.", "completed": [], "remaining": [0.4201909085327074, 0.002111041365756349, 0.0022973685120990517, 0.2358379652523434], "speed_mps": 6.106486859339244e-62, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "move forward 1 meter", "target": [1, 0, 0, 0]}, {"objective": "turn right 15 degrees", "target": [1, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"streamed actions"`
