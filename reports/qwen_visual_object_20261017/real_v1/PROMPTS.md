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
Never claim completion. No prose, no extra keys. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "feedback": "initial mission"}
```

Response: `"{\"steps\":[{\"objective\":\"Find the red pillar in the camera view and approach it.\",\"target\":[1,0,0,0]},{\"objective\":\"Stop nearby while keeping the red pillar visible.\",\"target\":[0,0,0,0]}]}"`

### 5: direction (observation 76)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Find the red pillar in the camera view and approach it.", "authorized_target": [1, 0, 0, 0], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[1, 0, 0, 0]}"`

### 6: pilot (observation 107)

```text
{"instruction": "Find the red pillar in the camera view and approach it.", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [0.9999999999999999, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.07063350588235284, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0842202352941177, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1113936941176471, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.15215388235294125, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151552, 151515, 151539, 151484, 151550, 151515, 151539, 151484, 151546, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151540, 151515, 151539, 151484, 151541, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.9999999999999999, 0.0, 0.0, -0.0]}`

### 7: pilot (observation 138)

```text
{"instruction": "Find the red pillar in the camera view and approach it.", "box": null, "state": [0.06906251069153982, 0.00011341851828867988, -0.0005202021404016044, -0.07726577238183449], "remaining": [0.9309367957726199, 0.0011419896264182605, 0.0005202021404016044, 0.07726577238183449]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, 0.00706895882352937, -0.0005490470588235263, -0.0009852058823529575], [0.09101360000000003, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.09101360000000003, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.0842202352941177, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.0842202352941177, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.07063350588235284, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.07063350588235284, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575], [0.07063350588235284, 0.003601229411764717, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151549, 151513, 151539, 151484, 151549, 151514, 151539, 151484, 151549, 151514, 151539, 151484, 151550, 151514, 151539, 151484, 151550, 151514, 151539, 151484, 151552, 151514, 151539, 151484, 151552, 151514, 151539, 151484, 151552, 151514, 151539, 151484], "remaining_supplied": [0.9309367957726199, 0.0011419896264182605, 0.0005202021404016044, 0.07726577238183449]}`

### 8: pilot (observation 169)

```text
{"instruction": "Find the red pillar in the camera view and approach it.", "box": null, "state": [0.29338595557355196, 0.010714342943493965, -0.0019080068843320142, -0.22199628321729134], "remaining": [0.7066502538211754, -0.007976446569830986, 0.0019080068843320142, 0.22199628321729134]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, -0.0033342294117646998, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151516, 151539, 151484, 151542, 151516, 151539, 151484, 151542, 151516, 151539, 151484, 151542, 151516, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7066502538211754, -0.007976446569830986, 0.0019080068843320142, 0.22199628321729134]}`

### 9: monitor (observation 193)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it.", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4708066315487697, "heading_error_deg": 0.3243349077440387, "speed_mps": 0.1929550816079773, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet stopped.\"\n}"`

### 10: direction (observation 235)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Stop nearby while keeping the red pillar visible.", "authorized_target": [1, 0, 0, 0], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[1, 0, 0, 0]}"`

### 11: monitor (observation 306)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Stop nearby while keeping the red pillar visible.", "active_step": 1, "is_last_step": true, "numeric_target": true, "position_error_m": 0.41284574715825645, "heading_error_deg": 0.3243349077440387, "speed_mps": 4.272032599636907e-09, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"stop\", \"reason\": \"Red pillar visible, position/heading acceptable, stationary\"}"`
