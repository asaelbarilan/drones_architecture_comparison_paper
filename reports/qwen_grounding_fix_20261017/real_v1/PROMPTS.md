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
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: 
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

### 5: direction (observation 96)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    500,\n    300\n  ]\n}"`

### 6: pilot (observation 152)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}
```

Response: `{"steps_fru_m_yaw_rad": [[-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, 0.0001335000000000086, 0.1924040823529412, -0.003860441176470608]], "tokens": [151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485, 151563, 151515, 151387, 151485], "remaining_supplied": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}`

### 7: pilot (observation 183)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [-0.003882393130144479, 0.0001291127383400354, 0.1824853539783926, -0.30245161614825217], "remaining": [1.0692836159563255, -0.0944859461423681, 0.4141841450693975, -5.062269251133079]}
```

Response: `{"steps_fru_m_yaw_rad": [[-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [-0.00409350588235291, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608]], "tokens": [151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485, 151563, 151516, 151387, 151485], "remaining_supplied": [1.0692836159563255, -0.0944859461423681, 0.4141841450693975, -5.062269251133079]}`

### 8: pilot (observation 214)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [-0.01426416870916413, -0.006756498803837544, 0.6678731359051215, -0.8689449319710251], "remaining": [1.0804416943857924, -0.07686704430249447, -0.07120363685733144, -4.495775935310307]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485, 151560, 151518, 151539, 151485], "remaining_supplied": [1.0804416943857924, -0.07686704430249447, -0.07120363685733144, -4.495775935310307]}`

### 9: pilot (observation 245)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.017693462872406578, -0.030479526051481593, 0.7559272289986536, -1.43701553219433], "remaining": [1.0486081843434873, -0.043237051896177325, -0.1592577299508635, -3.9277053350870013]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485], "remaining_supplied": [1.0486081843434873, -0.043237051896177325, -0.1592577299508635, -3.9277053350870013]}`

### 10: pilot (observation 276)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.21651339373308215, -0.047766258300000884, 0.7552298873149099, -2.00449162603541], "remaining": [0.8496820564986975, -0.022527481385280712, -0.15856038826711982, -3.360229241245922]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485], "remaining_supplied": [0.8496820564986975, -0.022527481385280712, -0.15856038826711982, -3.360229241245922]}`

### 11: pilot (observation 307)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.4476519527290729, -0.06476687651289922, 0.7538250479324922, -2.571458812857993], "remaining": [0.6181948210893354, -0.007505149116437709, -0.15715554888470207, -2.7932620544233386]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485, 151550, 151516, 151539, 151485], "remaining_supplied": [0.6181948210893354, -0.007505149116437709, -0.15715554888470207, -2.7932620544233386]}`

### 12: monitor (observation 329)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.49255696086332473, "heading_error_deg": 2.3919264956288755, "speed_mps": 0.16500559512855806, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet stationary.\"\n}"`

### 13: direction (observation 371)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    433,\n    0,\n    600,\n    380\n  ]\n}"`

### 14: pilot (observation 428)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.6477114460961035, -0.08147500582383832, 0.7525700866644431, -2.9727943716524563], "remaining": [1.0568291147669375, 0.03200247846260823, 0.5170696247333417, 1.7342260089081225]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.003601229411764717, 0.1924040823529412, 0.0018900294117646932]], "tokens": [151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483, 151542, 151514, 151387, 151483], "remaining_supplied": [1.0568291147669375, 0.03200247846260823, 0.5170696247333417, 1.7342260089081225]}`

### 15: pilot (observation 459)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [0.9259398796134677, -0.08835240678209422, 1.1388853379735986, -2.706153257351085], "remaining": [0.7787237383848233, 0.02081744531332924, 0.13075437342418628, 1.4675848946067513]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7787237383848233, 0.02081744531332924, 0.13075437342418628, 1.4675848946067513]}`

### 16: monitor (observation 488)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4606034704815703, "heading_error_deg": 1.2400123389881446, "speed_mps": 0.17571102056128254, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet stationary.\"\n}"`

### 17: direction (observation 531)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    420,\n    0,\n    640,\n    430\n  ]\n}"`

### 18: pilot (observation 588)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [1.2961094297972293, -0.08908479368079175, 1.2882764501205664, -2.4785807017324784], "remaining": [1.0518457548109712, 0.059997067864015124, 0.4673053629713264, 3.2645648455559138]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759], [0.1385671529411765, 0.02093987647058826, 0.10039994117647061, 0.01051573529411759]], "tokens": [151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480, 151542, 151509, 151460, 151480], "remaining_supplied": [1.0518457548109712, 0.059997067864015124, 0.4673053629713264, 3.2645648455559138]}`

### 19: pilot (observation 619)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [1.5751516647187667, -0.057326798072219076, 1.4894845507129295, -0.9957305854806788], "remaining": [0.7745978855893725, -0.003844770971053596, 0.26609726237896325, 1.7817147293041147]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151516, 151465, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7745978855893725, -0.003844770971053596, 0.26609726237896325, 1.7817147293041147]}`

### 20: monitor (observation 649)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4493578829500211, "heading_error_deg": 1.5431427832143, "speed_mps": 0.17299142266499498, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet at target distance.\"\n}"`

### 21: direction (observation 692)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    480\n  ]\n}"`

### 22: pilot (observation 747)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [1.9450612361615598, -0.061729719483847534, 1.7448888734741095, -0.7571586393908643], "remaining": [1.046864904912469, 1.2516364440440242e-06, 0.4175325844796429, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.046864904912469, 1.2516364440440242e-06, 0.4175325844796429, -0.0]}`

### 23: pilot (observation 778)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [2.2773333918611516, -0.05850774267204062, 1.9102719922900109, -0.4904723678640651], "remaining": [0.7146211702327493, -0.010937612028748156, 0.2521494656637415, -0.2666862715267992]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151516, 151465, 151483, 151541, 151516, 151465, 151483, 151541, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7146211702327493, -0.010937612028748156, 0.2521494656637415, -0.2666862715267992]}`

### 24: monitor (observation 803)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.45639218938417325, "heading_error_deg": 0.44120244428471705, "speed_mps": 0.17405299229611176, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"continue\",\n  \"reason\": \"Red pillar visible; approach ongoing; not yet stationary.\"\n}"`

### 25: direction (observation 844)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Approach the red pillar", "authorized_target": "Approach the red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    360,\n    0,\n    640,\n    540\n  ]\n}"`

### 26: pilot (observation 900)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [2.5886782873750462, -0.06485801877826602, 2.1001940701109056, -0.3159561951061472], "remaining": [1.0408536551424064, 1.7183723969582676e-06, 0.3578211027233795, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.1657406117647059, 0.003601229411764717, 0.08251024705882354, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151538, 151514, 151474, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0408536551424064, 1.7183723969582676e-06, 0.3578211027233795, -0.0]}`

### 27: pilot (observation 931)

```text
{"instruction": "Approach the red pillar", "box": null, "state": [2.921347369745102, -0.059069401397018884, 2.265792032797207, -0.04919366526246218], "remaining": [0.7081783920405329, -0.01091860053867727, 0.1922231400370782, -0.26676252984368504]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1657406117647059, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.1657406117647059, 0.0001335000000000086, 0.07612107058823528, -0.0009852058823529575], [0.1657406117647059, 0.0001335000000000086, 0.07484323529411765, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151538, 151515, 151474, 151484, 151538, 151515, 151479, 151484, 151538, 151515, 151480, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7081783920405329, -0.01091860053867727, 0.1922231400370782, -0.26676252984368504]}`

### 28: monitor (observation 954)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Approach the red pillar", "active_step": 0, "is_last_step": false, "numeric_target": false, "position_error_m": 0.4513940134590513, "heading_error_deg": 0.18726597216669064, "speed_mps": 0.17995808203996821, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 29: direction (observation 996)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Stop nearby while keeping the red pillar visible", "authorized_target": "Stop nearby while keeping the red pillar visible", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": false,\n  \"box\": null\n}"`

### 30: direction (observation 1061)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Stop nearby while keeping the red pillar visible", "authorized_target": "Stop nearby while keeping the red pillar visible", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": false,\n  \"box\": null\n}"`

### 31: direction (observation 1129)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Stop nearby while keeping the red pillar visible", "authorized_target": "Stop nearby while keeping the red pillar visible", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": false,\n  \"box\": null\n}"`
