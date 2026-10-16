# Exact model prompts

One shared Qwen base; pilot uses the trained adapter. Other roles disable it. No separate system message is supplied.

## planner template

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: 
```

## direction template

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: 
```

## monitor template

```text
Assess ONLY the active step, preserving the original mission.
Return JSON only {"status":"stop","reason":"short evidence"}.
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
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "plan": null, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"steps\":[]}"`

### 5: planner (observation 11)

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "plan": null, "feedback": "planner requires 1..8 steps", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"steps\":[]}"`

### 6: planner (observation 21)

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"mission": "Hold the starting position and heading without moving. Confirm completion once stationary.", "plan": null, "feedback": "planner requires 1..8 steps", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"steps\":[]}"`

## Actual calls: forward

### 11: planner (observation 1)

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "plan": null, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"steps\": [\n    {\n      \"objective\": \"Move forward 1 meter from the starting position, maintain altitude and heading\",\n      \"target\": [\n        1.0,\n        0.0,\n        0.0,\n        0.0\n      ]\n    }\n  ]\n}"`

### 12: direction (observation 94)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: {"mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "plan": {"objective": "Move forward 1 meter from the starting position, maintain altitude and heading", "target": [1.0, 0.0, 0.0, 0.0]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 1 meter from the starting position, maintain altitude and heading", "target": [1.0, 0.0, 0.0, 0.0]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1.0,0.0,0.0,0.0],\"terminal\":true}"`

### 13: pilot (observation 139)

```text
{"instruction": "Move forward 1 meter from the starting position, maintain altitude and heading", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0000000000000002, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0000000000000002, 0.0, 0.0, -0.0]}`

### 14: pilot (observation 170)

```text
{"instruction": "Move forward 1 meter from the starting position, maintain altitude and heading", "box": null, "state": [0.1892922298563326, 9.551505959301543e-05, -0.0005204129676603664, -0.0771602820996157], "remaining": [0.810707163622733, 0.0009962656410215515, 0.0005204129676603664, 0.0771602820996157]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.810707163622733, 0.0009962656410215515, 0.0005204129676603664, 0.0771602820996157]}`

### 15: monitor (observation 196)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON only {"status":"stop","reason":"short evidence"}.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "plan": {"objective": "Move forward 1 meter from the starting position, maintain altitude and heading", "target": [1.0, 0.0, 0.0, 0.0]}, "feedback": "initial mission", "completed": [], "remaining": [0.4365093218555596, 0.0015141582370476955, 0.0015491738755306628, 0.1736984652060257], "speed_mps": 0.17302651763942156, "event": "arrival", "local_goal_terminal": true, "ordered_steps": [{"objective": "Move forward 1 meter from the starting position, maintain altitude and heading", "target": [1.0, 0.0, 0.0, 0.0]}], "active_step": 0, "is_last_step": true, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\":\"stop\",\"reason\":\"short evidence\"}"`

## Actual calls: turn

### 20: planner (observation 1)

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": null, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"steps\": [\n    {\n      \"objective\": \"Move forward 0.1 meters with original heading\",\n      \"target\": [0.1, 0, 0, 0]\n    },\n    {\n      \"objective\": \"Turn right 15 degrees at current position\",\n      \"target\": [0, 0, 0, 15]\n    }\n  ]\n}"`

### 21: direction (observation 122)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[0.1,0,0,0],\"terminal\":false}"`

### 22: monitor (observation 199)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON only {"status":"stop","reason":"short evidence"}.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, "feedback": "initial mission", "completed": [], "remaining": [0.10000000000000002, 0.0, 0.0, -0.0], "speed_mps": 0.0, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\":\"continue\",\"reason\":\"short evidence\"}"`

### 23: monitor (observation 264)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON only {"status":"stop","reason":"short evidence"}.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, "feedback": "short evidence", "completed": [], "remaining": [0.10000000000000002, 0.0, 0.0, -0.0], "speed_mps": 0.0, "event": "arrival", "local_goal_terminal": false, "ordered_steps": [{"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\":\"stop\",\"reason\":\"short evidence\"}"`

### 24: direction (observation 289)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}, "feedback": "intermediate goal reached; advance mission", "completed": [{"plan": {"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, "result": "short evidence"}], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}], "active_step": 1, "is_last_step": true, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[0,0,0,15],\"terminal\":true}"`

### 25: pilot (observation 324)

```text
{"instruction": "Turn right 15 degrees at current position", "box": null, "state": [0.0, -0.0, 0.0, -0.0], "remaining": [0.0, -0.0, 0.0, 14.999999999999996]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.0, -0.0, 0.0, 14.999999999999996]}`

### 26: pilot (observation 355)

```text
{"instruction": "Turn right 15 degrees at current position", "box": null, "state": [0.005658153464668519, 0.0004855470844008184, -0.0011542851296075796, 7.886427359925307], "remaining": [-0.005671260485401151, 0.00029539991137101794, 0.0011542851296075796, 7.113572640074689]}
```

Response: `"streamed actions"`

### 27: monitor (observation 367)

```text
Assess ONLY the active step, preserving the original mission.
Return JSON only {"status":"stop","reason":"short evidence"}.
Status meanings: stop=active step complete; continue=more motion needed;
hold=temporary unsafe/uncertain pause; replan=refresh current local goal.
For numeric targets, measured pose is authoritative: return stop when
position_and_heading_acceptable AND stationary are true. Do not demand visible
landmarks, exact zero error or extra precision. A hold-position task is complete
when these checks pass without movement. Otherwise never return stop.
For visual tasks also require visible accomplishment; do not infer identity
from numeric arrival alone. Intermediate stop advances exactly one step; only
the last step can complete the mission. Context: {"mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "plan": {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}, "feedback": "intermediate goal reached; advance mission", "completed": [{"plan": {"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, "result": "short evidence"}], "remaining": [-0.0052308912304449545, 0.0004520184811894767, 0.0015731520502626495, 4.939204451201038], "speed_mps": 0.004072039099329258, "event": "arrival", "local_goal_terminal": true, "ordered_steps": [{"objective": "Move forward 0.1 meters with original heading", "target": [0.1, 0, 0, 0]}, {"objective": "Turn right 15 degrees at current position", "target": [0, 0, 0, 15]}], "active_step": 1, "is_last_step": true, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\":\"stop\",\"reason\":\"short evidence\"}"`

## Actual calls: move_then_turn

### 32: planner (observation 1)

```text
Plan the ENTIRE original mission in execution order. JSON only:
{"steps":[{"objective":"short instruction","target":[0,0,0,0]}]}.
Each explicit ordered movement is a separate step. Preserve EVERY requirement.
For numeric steps target is [forward_m,right_m,up_m,clockwise_degrees] relative
to EPISODE START. Carry forward earlier position/heading into later targets.
First move then turn needs TWO steps: movement with original heading, then turn
at the reached target position. Hold starting pose is one zero target step.
Do not create a separate stop step: each step ends stationary at its target.
For nonnumeric visual steps target is a visual-description string instead.
Never claim completion. No prose, no extra keys. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": null, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"steps\": [\n    {\n      \"objective\": \"Move forward 1 meter from the starting position while maintaining heading.\",\n      \"target\": [1.0, 0.0, 0.0, 0.0]\n    },\n    {\n      \"objective\": \"Turn right 15 degrees from the starting heading without moving further.\",\n      \"target\": [0.0, 0.0, 0.0, 15.0]\n    }\n  ]\n}"`

### 33: direction (observation 147)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "Move forward 1 meter from the starting position while maintaining heading.", "target": [1.0, 0.0, 0.0, 0.0]}, "feedback": "initial mission", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 1 meter from the starting position while maintaining heading.", "target": [1.0, 0.0, 0.0, 0.0]}, {"objective": "Turn right 15 degrees from the starting heading without moving further.", "target": [0.0, 0.0, 0.0, 15.0]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1.0,0.0,0.0,0.0],\"terminal\":true}"`

### 34: direction (observation 193)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "Move forward 1 meter from the starting position while maintaining heading.", "target": [1.0, 0.0, 0.0, 0.0]}, "feedback": "direction cannot skip remaining mission steps", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 1 meter from the starting position while maintaining heading.", "target": [1.0, 0.0, 0.0, 0.0]}, {"objective": "Turn right 15 degrees from the starting heading without moving further.", "target": [0.0, 0.0, 0.0, 15.0]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1.0,0.0,0.0,0.0],\"terminal\":true}"`

### 35: direction (observation 240)

```text
Authorize one persistent local goal. Return JSON only:
{"kind":"relative","target":[0,0,0,0],"terminal":true}
for explicit numeric motion. These offsets are relative to the EPISODE START,
not the current pose. Never add the same displacement again when replanning.
Copy the committed active plan.target exactly for numeric steps. Set terminal
to is_last_step. Never combine steps or omit an unfinished step.
For a visual objective use:
{"kind":"visual","target":{"u":500,"v":500,"travel_m":1.0,
"target_visible":false,"box":null},"terminal":false}.
Visual u,v and box coordinates are normalized 0..1000. Travel is 0.25..3m.
Only give a box when the object is actually visible. Choose a camera point toward
the objective or visible free space. Terminal means the goal completes the task.
Use exactly kind,target,terminal; no explanation. Context: {"mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "plan": {"objective": "Move forward 1 meter from the starting position while maintaining heading.", "target": [1.0, 0.0, 0.0, 0.0]}, "feedback": "direction cannot skip remaining mission steps", "completed": [], "remaining": null, "speed_mps": 0.0, "event": null, "local_goal_terminal": null, "ordered_steps": [{"objective": "Move forward 1 meter from the starting position while maintaining heading.", "target": [1.0, 0.0, 0.0, 0.0]}, {"objective": "Turn right 15 degrees from the starting heading without moving further.", "target": [0.0, 0.0, 0.0, 15.0]}], "active_step": 0, "is_last_step": false, "position_and_heading_acceptable": false, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"kind\":\"relative\",\"target\":[1.0,0.0,0.0,0.0],\"terminal\":true}"`
