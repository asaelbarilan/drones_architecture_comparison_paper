# Exact model prompts

One shared Qwen base; pilot uses the trained adapter. Other roles disable it. No separate system message is supplied.

## planner template

```text
Plan the original visual mission in order. Return ONLY JSON with
one key steps, a list of objects each having objective and target strings.
Each target is the object's identifying NOUN PHRASE, not an action instruction.
Each objective preserves the requested action, object identity and stop condition.
Approach an object and stop nearby is ONE step, not approach followed by stop.
Use multiple steps only for distinct explicitly requested destinations/actions.
Do not invent coordinates or numeric moves. Preserve the entire original goal.
Context: 
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
Plan the original visual mission in order. Return ONLY JSON with
one key steps, a list of objects each having objective and target strings.
Each target is the object's identifying NOUN PHRASE, not an action instruction.
Each objective preserves the requested action, object identity and stop condition.
Approach an object and stop nearby is ONE step, not approach followed by stop.
Use multiple steps only for distinct explicitly requested destinations/actions.
Do not invent coordinates or numeric moves. Preserve the entire original goal.
Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "feedback": "initial mission", "task_contract": "VISUAL object task. Each target MUST be a visual-description string. Never invent numeric movements or coordinates. Approach and stop nearby are one visual objective, not a numeric step plus a separate stop step."}
```

Response: `"{\n  \"steps\": [\n    {\n      \"objective\": \"Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.\",\n      \"target\": \"red pillar\"\n    }\n  ]\n}"`

### 5: direction (observation 78)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    500,\n    300\n  ]\n}"`

### 6: pilot (observation 136)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608]], "tokens": [151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485], "remaining_supplied": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}`

### 7: pilot (observation 167)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.013955526224746603, -0.00286374777526679, 0.16488151765502757, -0.28055901483878076], "remaining": [1.0513950744928109, -0.09198903191405214, 0.43178798139276253, -5.084161852442551]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608]], "tokens": [151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485], "remaining_supplied": [1.0513950744928109, -0.09198903191405214, 0.43178798139276253, -5.084161852442551]}`

### 8: pilot (observation 198)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.053156861825395224, -0.025073787990121072, 0.6298096811138256, -0.8249705702412881], "remaining": [1.0127046074629404, -0.06035159225702505, -0.03314018206603553, -4.539750297040044]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.020672876470588242, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.017205147058823533, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.013737417647058825, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151521, 151539, 151485, 151550, 151520, 151539, 151485, 151550, 151519, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485], "remaining_supplied": [1.0127046074629404, -0.06035159225702505, -0.03314018206603553, -4.539750297040044]}`

### 9: pilot (observation 229)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.2354092717880364, -0.06989070297034686, 0.7176525843190187, -1.3690215023810801], "remaining": [0.8299608745915676, -0.01028308991545479, -0.12098308527122859, -3.9956993649002523]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485], "remaining_supplied": [0.8299608745915676, -0.01028308991545479, -0.12098308527122859, -3.9956993649002523]}`

### 10: pilot (observation 260)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.4654581273851619, -0.08996281055550061, 0.7169544998397472, -1.9355582593280012], "remaining": [0.5994264338182622, 0.01021452971414194, -0.12028500079195714, -3.42916260795333]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485], "remaining_supplied": [0.5994264338182622, 0.01021452971414194, -0.12028500079195714, -3.42916260795333]}`

### 11: monitor (observation 278)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4950674795213654, "heading_error_deg": 3.117907749743558, "speed_mps": 0.16254528088175357, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 12: direction (observation 320)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [433, 0, 600, 380]\n}"`

### 13: pilot (observation 368)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.6334112544070014, -0.08723819127098953, 0.715931404832125, -2.2468131175377737], "remaining": [1.0568312325686564, 0.031994537225092545, 0.5170696020357872, 1.7342260089081225]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932]], "tokens": [151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483], "remaining_supplied": [1.0568312325686564, 0.031994537225092545, 0.5170696020357872, 1.7342260089081225]}`

### 14: pilot (observation 399)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.9114969270116973, -0.08363854684728389, 1.1015916581055993, -1.9799733547607985], "remaining": [0.7791734995968245, 0.013866894937366286, 0.13140934876231292, 1.4673862461311475]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7791734995968245, 0.013866894937366286, 0.13140934876231292, 1.4673862461311475]}`

### 15: monitor (observation 428)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.46270224380597613, "heading_error_deg": 1.2397425435171112, "speed_mps": 0.17311441687359763, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 16: direction (observation 470)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    400\n  ]\n}"`

### 17: pilot (observation 527)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.282401430037021, -0.07807177722718456, 1.1900473220546717, -1.7523296521467624], "remaining": [1.0548290752919705, -3.496782052803127e-06, 0.4971679599374177, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1657406117647059, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151538, 151516, 151465, 151483, 151538, 151516, 151465, 151483, 151538, 151516, 151465, 151483, 151538, 151516, 151465, 151483, 151538, 151516, 151465, 151483, 151538, 151516, 151465, 151483, 151538, 151516, 151465, 151483, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0548290752919705, -3.496782052803127e-06, 0.4971679599374177, -0.0]}`

### 18: pilot (observation 558)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.6141226854126547, -0.09450927706881374, 1.378397899707661, -1.485505548206266], "remaining": [0.7227817252651568, 0.002916639408907934, 0.30881738228442845, -0.2668241039404964]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, 0.09401076470588235, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151513, 151465, 151483, 151542, 151513, 151464, 151483, 151542, 151513, 151464, 151483, 151542, 151513, 151464, 151483, 151542, 151513, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7227817252651568, 0.002916639408907934, 0.30881738228442845, -0.2668241039404964]}`

### 19: monitor (observation 584)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4543597969179153, "heading_error_deg": 0.46300684340547055, "speed_mps": 0.17346462589480147, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 20: direction (observation 625)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    450\n  ]\n}"`

### 21: pilot (observation 680)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.9427346280171096, -0.09170550181300785, 1.593670480832028, -1.2893228087412918], "remaining": [1.0498405110199054, -3.3641355706715004e-06, 0.44736976688184615, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151516, 151465, 151483, 151542, 151516, 151465, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0498405110199054, -3.3641355706715004e-06, 0.44736976688184615, -0.0]}`

### 22: pilot (observation 711)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.2201652205677904, -0.10430212880483908, 1.7823117106355966, -1.0224513384448946], "remaining": [0.7722179106106369, 0.002750817028697089, 0.2587285370782775, -0.26687147029639724]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, 0.09401076470588235, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151465, 151483, 151541, 151513, 151464, 151483, 151541, 151513, 151464, 151483, 151541, 151513, 151464, 151483, 151541, 151513, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7722179106106369, 0.002750817028697089, 0.2587285370782775, -0.26687147029639724]}`

### 23: monitor (observation 741)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4481391178853679, "heading_error_deg": 0.49451489135457827, "speed_mps": 0.17638833119567923, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 24: direction (observation 781)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    380,\n    0,\n    650,\n    530\n  ]\n}"`

### 25: pilot (observation 835)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.591011717625956, -0.09738707058550822, 2.0258233864420134, -0.7948079173867135], "remaining": [1.0418396332089903, 0.029996073995883693, 0.36776209240959457, 1.6492522851130313]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1657406117647059, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151538, 151513, 151387, 151483, 151538, 151513, 151387, 151483, 151538, 151513, 151387, 151483, 151538, 151513, 151387, 151483, 151538, 151513, 151387, 151483, 151538, 151513, 151387, 151483, 151538, 151513, 151387, 151483, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0418396332089903, 0.029996073995883693, 0.36776209240959457, 1.6492522851130313]}`

### 26: pilot (observation 866)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.9236212778320763, -0.08742539011273764, 2.4117639774319724, -0.5276776106389734], "remaining": [0.7094644486206864, 0.01211394027226681, -0.018178498580364355, 1.3821219783652916]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151513, 151539, 151483, 151536, 151513, 151539, 151483, 151536, 151513, 151539, 151483, 151536, 151513, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7094644486206864, 0.01211394027226681, -0.018178498580364355, 1.3821219783652916]}`

### 27: monitor (observation 888)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4450351103132172, "heading_error_deg": 1.2297079608600843, "speed_mps": 0.1770785164901694, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position heading acceptable, stationary.\"\n}"`

### 28: direction (observation 928)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    333,\n    0,\n    666,\n    666\n  ]\n}"`

### 29: pilot (observation 984)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.2536936273265242, -0.07721877846719516, 2.5008290336088237, -0.3752635931337663], "remaining": [1.0282445426638704, -0.0020039277131422006, 0.23249259689066903, -0.1114324682726271]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0282445426638704, -0.0020039277131422006, 0.23249259689066903, -0.1114324682726271]}`

### 30: pilot (observation 1015)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.613110973858435, -0.07887851580773142, 2.5586346671917486, -0.10837774183131493], "remaining": [0.6688042102657118, -0.005813610146422732, 0.17468696330774414, -0.37831831957507844]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151515, 151474, 151484, 151541, 151515, 151474, 151484, 151541, 151515, 151474, 151484, 151541, 151515, 151474, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.6688042102657118, -0.005813610146422732, 0.17468696330774414, -0.37831831957507844]}`

### 31: monitor (observation 1034)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.46739192113295547, "heading_error_deg": 0.31043361825684246, "speed_mps": 0.18426849319535293, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 32: direction (observation 1076)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    280,\n    0,\n    720,\n    740\n  ]\n}"`

### 33: pilot (observation 1131)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.8717741098147296, -0.07933506379253019, 2.6714205933320025, -0.17626244314955095], "remaining": [1.0208904961391467, -1.1445559286449303e-07, 0.15883020564608152, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.07612107058823528, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.07612107058823528, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.07612107058823528, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.07612107058823528, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151515, 151474, 151484, 151536, 151515, 151479, 151484, 151536, 151515, 151479, 151484, 151536, 151515, 151479, 151484, 151536, 151515, 151479, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0208904961391467, -1.1445559286449303e-07, 0.15883020564608152, -0.0]}`

### 34: pilot (observation 1162)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [4.231190118772908, -0.08039559764745785, 2.830144912565798, -0.31537924300857884], "remaining": [0.6614710854645038, 0.0015608084783661491, 0.00010588641228626017, 0.13911679985902792]}
```

Response: `"streamed actions"`

### 35: monitor (observation 1179)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.46730321410180053, "heading_error_deg": 0.19556493886934012, "speed_mps": 0.18039441870595407, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"streamed actions"`
