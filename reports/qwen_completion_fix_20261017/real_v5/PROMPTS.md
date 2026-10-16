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

### 5: direction (observation 34)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Hold position and heading", "authorized_target": [0, 0, 0, 0], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[0,0,0,0]}"`

### 6: monitor (observation 100)

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

### 12: direction (observation 36)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Move forward 1 meter", "authorized_target": [1, 0, 0, 0], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 13: pilot (observation 63)

```text
{"instruction": "Move forward 1 meter", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0000000000000002, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0000000000000002, 0.0, 0.0, -0.0]}`

### 14: pilot (observation 94)

```text
{"instruction": "Move forward 1 meter", "box": null, "state": [0.18952227760869947, 9.547141904915624e-05, -0.0005210454279520604, -0.07736895957991011], "remaining": [0.8104771123872888, 0.0009989513221649732, 0.0005210454279520604, 0.0773689595799101]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.19970743529411772, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151533, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.8104771123872888, 0.0009989513221649732, 0.0005210454279520604, 0.0773689595799101]}`

### 15: monitor (observation 120)

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
the last step can complete the mission. Context: {"original_mission": "Move forward 1 meter from the starting position, maintain altitude and heading, then stop.", "active_objective": "Move forward 1 meter", "active_step": 0, "is_last_step": true, "numeric_target": true, "position_error_m": 0.4362934997754306, "heading_error_deg": 0.17385806667426631, "speed_mps": 0.17391840986316112, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
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

### 21: direction (observation 48)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "Turn right 15 degrees from the starting heading without changing position", "authorized_target": [0, 0, 0, 15], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[0,0,0,15]}"`

### 22: pilot (observation 76)

```text
{"instruction": "Turn right 15 degrees from the starting heading without changing position", "box": null, "state": [0.0, -0.0, 0.0, -0.0], "remaining": [0.0, -0.0, 0.0, 14.999999999999996]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151465, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.0, -0.0, 0.0, 14.999999999999996]}`

### 23: pilot (observation 107)

```text
{"instruction": "Turn right 15 degrees from the starting heading without changing position", "box": null, "state": [0.002565132539910446, 0.00014993644853112916, -0.000522006348831372, 4.209953340724169], "remaining": [-0.0025692181954978643, 3.877821331940202e-05, 0.000522006348831372, 10.790046659275827]}
```

Response: `{"steps_fru_m_yaw_rad": [[-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [-0.00409350588235291, 0.0001335000000000086, -0.0005490470588235263, 0.0823966176470588], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151563, 151515, 151539, 151455, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [-0.0025692181954978643, 3.877821331940202e-05, 0.000522006348831372, 10.790046659275827]}`

### 24: monitor (observation 125)

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
the last step can complete the mission. Context: {"original_mission": "Turn right 15 degrees from the starting heading without changing position, then stop.", "active_objective": "Turn right 15 degrees from the starting heading without changing position", "active_step": 0, "is_last_step": true, "numeric_target": true, "position_error_m": 0.0012423474619826472, "heading_error_deg": 4.625768805694449, "speed_mps": 0.0068571558461627295, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
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

### 30: direction (observation 65)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "move forward 1 meter", "authorized_target": [1, 0, 0, 0], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[1,0,0,0]}"`

### 31: pilot (observation 91)

```text
{"instruction": "move forward 1 meter", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0, 0.0, 0.0, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0, 0.0, 0.0, -0.0]}`

### 32: pilot (observation 122)

```text
{"instruction": "move forward 1 meter", "box": null, "state": [0.29175530878101896, 8.688945709786519e-05, -0.0011560269641734955, -0.14471069753831534], "remaining": [0.7082426517105872, 0.0017019070490048981, 0.0011560269641734955, 0.14471069753834076]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151542, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7082426517105872, 0.0017019070490048981, 0.0011560269641734955, 0.14471069753834076]}`

### 33: monitor (observation 144)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "move forward 1 meter", "active_step": 0, "is_last_step": false, "numeric_target": true, "position_error_m": 0.4780346614703007, "heading_error_deg": 0.2356471366735877, "speed_mps": 0.1912792562793811, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"continue\", \"reason\": \"Position error 0.478m exceeds 0.5m tolerance.\"}"`

### 34: direction (observation 189)

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
the objective or visible free space. Use exactly kind,target; no explanation. Context: {"active_objective": "turn right 15 degrees", "authorized_target": [1, 0, 0, 15], "numeric_target": true}
```

Response: `"{\"kind\":\"relative\",\"target\":[1, 0, 0, 15]}"`

### 35: pilot (observation 221)

```text
{"instruction": "turn right 15 degrees", "box": null, "state": [0.5794412090240866, -0.0003802007851107851, -0.0022959311644275004, -0.2356471366736131], "remaining": [0.4205536703546928, 0.0021098746302875256, 0.0022959311644275004, 15.23564713667362]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, 0.027767147058823494], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, 0.027767147058823494], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, 0.027767147058823494], [0.1385671529411765, 0.0001335000000000086, -0.0005490470588235263, 0.027767147058823494], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151515, 151539, 151474, 151542, 151515, 151539, 151474, 151542, 151515, 151539, 151474, 151542, 151515, 151539, 151474, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.4205536703546928, 0.0021098746302875256, 0.0022959311644275004, 15.23564713667362]}`

### 36: pilot (observation 252)

```text
{"instruction": "turn right 15 degrees", "box": null, "state": [0.7109670929653011, -0.00018476152907638874, -0.0028171067548212747, 1.9429595128971915], "remaining": [0.28887299926418847, -0.009614872950991813, 0.0028171067548212747, 13.057040487102816]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.03666668235294124, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.03666668235294124, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.03666668235294124, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.03666668235294124, 0.0001335000000000086, -0.0005490470588235263, 0.053644264705882294], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151557, 151515, 151539, 151465, 151557, 151515, 151539, 151465, 151557, 151515, 151539, 151465, 151557, 151515, 151539, 151465, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.28887299926418847, -0.009614872950991813, 0.0028171067548212747, 13.057040487102816]}`

### 37: pilot (observation 283)

```text
{"instruction": "turn right 15 degrees", "box": null, "state": [0.8461540714315648, 0.006127851714636626, -0.004204086865960299, 9.843027465077228], "remaining": [0.15053373249589383, -0.032337527496321, 0.004204086865960299, 5.156972534922781]}
```

Response: `"streamed actions"`

### 38: monitor (observation 289)

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
the last step can complete the mission. Context: {"original_mission": "First move forward 1 meter from the starting position while maintaining heading. After reaching that position, turn right 15 degrees from the starting heading without moving further, then stop.", "active_objective": "turn right 15 degrees", "active_step": 1, "is_last_step": true, "numeric_target": true, "position_error_m": 0.13818739121423915, "heading_error_deg": 4.996135148944083, "speed_mps": 0.07237239198224715, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\"status\": \"stop\", \"reason\": \"Heading error within tolerance, stationary, mission complete\"}"`
