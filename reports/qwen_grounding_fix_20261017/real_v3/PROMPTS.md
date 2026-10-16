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

### 5: direction (observation 77)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    500,\n    300\n  ]\n}"`

### 6: pilot (observation 132)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608]], "tokens": [151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485], "remaining_supplied": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}`

### 7: pilot (observation 163)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.015459257740068814, -0.003175229340109936, 0.18265459316410926, -0.3027606143683506], "remaining": [1.0499252840466047, -0.09127808759696904, 0.41401490588368084, -5.061960252912981]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608]], "tokens": [151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485], "remaining_supplied": [1.0499252840466047, -0.09127808759696904, 0.41401490588368084, -5.061960252912981]}`

### 8: pilot (observation 194)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.056323569924393274, -0.026414219845322787, 0.6674630139850342, -0.8651110536971555], "remaining": [1.0095600546771504, -0.05834962662702059, -0.07079351493724406, -4.499609813584176]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.020672876470588242, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.017205147058823533, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.013737417647058825, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, -0.010269688235294117, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151521, 151539, 151485, 151550, 151520, 151539, 151485, 151550, 151519, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485, 151550, 151518, 151539, 151485], "remaining_supplied": [1.0095600546771504, -0.05834962662702059, -0.07079351493724406, -4.499609813584176]}`

### 9: pilot (observation 225)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.2385034384483867, -0.07125485472209575, 0.7527849273622773, -1.409979404464098], "remaining": [0.8268412168685266, -0.008402186881201978, -0.15611542831448721, -3.9547414628172333]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485], "remaining_supplied": [0.8268412168685266, -0.008402186881201978, -0.15611542831448721, -3.9547414628172333]}`

### 10: pilot (observation 256)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.4596509118872489, -0.09090258881916151, 0.752119171611433, -1.9541522106334028], "remaining": [0.6051948793616506, 0.011546314919093303, -0.15544967256364295, -3.410568656647929]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608], [0.0842202352941177, 0.00706895882352937, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485, 151550, 151513, 151539, 151485], "remaining_supplied": [0.6051948793616506, 0.011546314919093303, -0.15544967256364295, -3.410568656647929]}`

### 11: monitor (observation 277)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4943240371269566, "heading_error_deg": 3.0546894566299763, "speed_mps": 0.16323426852534864, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 12: direction (observation 319)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    433,\n    0,\n    600,\n    380\n  ]\n}"`

### 13: pilot (observation 375)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.644490023681369, -0.08744694036166895, 0.7509860290449031, -2.310031410651355], "remaining": [1.0568302674825458, 0.03199422466684451, 0.5170696132990957, 1.7342260089081225]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932]], "tokens": [151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483], "remaining_supplied": [1.0568302674825458, 0.03199422466684451, 0.5170696132990957, 1.7342260089081225]}`

### 14: pilot (observation 406)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.922631085150526, -0.08415371736051716, 1.1367178583199982, -2.0434267253442835], "remaining": [0.7791209372298462, 0.013867533210627975, 0.13133778402400065, 1.4676213236010505]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7791209372298462, 0.013867533210627975, 0.13133778402400065, 1.4676213236010505]}`

### 15: monitor (observation 435)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4631707874916444, "heading_error_deg": 1.2400623043210213, "speed_mps": 0.1731879986644135, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 16: direction (observation 474)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    400\n  ]\n}"`

### 17: pilot (observation 529)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.2930958598589295, -0.07900387933537717, 1.2246914327258622, -1.8158677060642543], "remaining": [1.0547861061301216, -5.496378837843707e-06, 0.49716732031146105, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.1385671529411765, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151516, 151465, 151483, 151542, 151516, 151465, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151542, 151516, 151464, 151483, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0547861061301216, -5.496378837843707e-06, 0.49716732031146105, -0.0]}`

### 18: pilot (observation 560)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.5706419816315904, -0.09416283746642273, 1.4134972907917245, -1.5495118078308068], "remaining": [0.7769201410593439, 0.0027393945598799263, 0.3083614622455988, -0.2663558982334476]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, 0.08251024705882354, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.08251024705882354, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.08251024705882354, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.08251024705882354, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.08251024705882354, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151513, 151474, 151483, 151542, 151513, 151474, 151483, 151542, 151513, 151474, 151483, 151542, 151513, 151474, 151483, 151542, 151513, 151474, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7769201410593439, 0.0027393945598799263, 0.3083614622455988, -0.2663558982334476]}`

### 19: monitor (observation 590)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4560796505848883, "heading_error_deg": 0.5158894413372254, "speed_mps": 0.19538218305218838, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 20: direction (observation 632)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    450\n  ]\n}"`

### 21: pilot (observation 688)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.9543585510161798, -0.0894655454306395, 1.6474418633951071, -1.299978264727029], "remaining": [1.0498407467175979, -3.456975796678474e-06, 0.44737605177994144, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.09401076470588235, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151516, 151465, 151483, 151541, 151516, 151465, 151483, 151541, 151516, 151464, 151483, 151541, 151516, 151464, 151483, 151541, 151516, 151464, 151483, 151541, 151516, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0498407467175979, -3.456975796678474e-06, 0.44737605177994144, -0.0]}`

### 22: pilot (observation 719)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.2457359297361466, -0.10242149410000778, 1.836303645268483, -1.0335511545236946], "remaining": [0.7582657096355898, 0.0028127763836617026, 0.25851426990656545, -0.2664271102033344]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, 0.09401076470588235, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.0952886, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151465, 151483, 151541, 151513, 151464, 151483, 151541, 151513, 151464, 151483, 151541, 151513, 151464, 151483, 151541, 151513, 151464, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7582657096355898, 0.0028127763836617026, 0.25851426990656545, -0.2664271102033344]}`

### 23: monitor (observation 748)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.44754377712346805, "heading_error_deg": 0.48300852710269826, "speed_mps": 0.17503493720227628, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 24: direction (observation 789)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    380,\n    0,\n    650,\n    540\n  ]\n}"`

### 25: pilot (observation 843)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.603973061826945, -0.09611231740727766, 2.0694782589746676, -0.8169697376243308], "remaining": [1.0408536597128686, 0.02999666301987322, 0.3578201918204842, 1.6508331773405134]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151514, 151460, 151483, 151541, 151514, 151460, 151483, 151541, 151514, 151460, 151483, 151541, 151514, 151460, 151483, 151541, 151514, 151460, 151483, 151541, 151514, 151460, 151483, 151541, 151514, 151460, 151483, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0408536597128686, 0.02999666301987322, 0.3578201918204842, 1.6508331773405134]}`

### 26: pilot (observation 874)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.8956200951994964, -0.09270045149722694, 2.270869875181644, -0.5505560121525573], "remaining": [0.7493811007079134, 0.01894249226695216, 0.15642857561350798, 1.38441945186874]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.10039994117647061, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151460, 151483, 151541, 151513, 151460, 151483, 151541, 151513, 151460, 151483, 151541, 151513, 151460, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7493811007079134, 0.01894249226695216, 0.15642857561350798, 1.38441945186874]}`

### 27: monitor (observation 902)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4521967501111513, "heading_error_deg": 1.1772517895712091, "speed_mps": 0.18226598034446687, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 28: direction (observation 942)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    333,\n    0,\n    666,\n    666\n  ]\n}"`

### 29: pilot (observation 997)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.2408708203625762, -0.08070767938077128, 2.5092491025269457, -0.34338834985502675], "remaining": [1.0282604165140352, -0.0020040534293357948, 0.23243712347883871, -0.1114324682726271]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.028841164705882355, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151536, 151515, 151516, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.0282604165140352, -0.0020040534293357948, 0.23243712347883871, -0.1114324682726271]}`

### 30: pilot (observation 1028)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.6006486164145763, -0.08216930867991856, 2.5671125787797093, -0.07725529224139269], "remaining": [0.6684605757422144, -0.005803661083973011, 0.17457364722607505, -0.3775655258862612]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151515, 151474, 151484, 151541, 151515, 151474, 151484, 151541, 151515, 151474, 151484, 151541, 151515, 151474, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.6684605757422144, -0.005803661083973011, 0.17457364722607505, -0.3775655258862612]}`

### 31: monitor (observation 1048)

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
the last step can complete the mission. Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_step": 0, "is_last_step": true, "numeric_target": false, "position_error_m": 0.4535810655616867, "heading_error_deg": 0.3039581348144468, "speed_mps": 0.1880111193558447, "position_and_heading_acceptable": true, "stationary": true, "tolerances": {"position_m": 0.5, "heading_deg": 5, "stopped_mps": 0.2}}
```

Response: `"{\n  \"status\": \"stop\",\n  \"reason\": \"Red pillar visible, position/heading acceptable, stationary.\"\n}"`

### 32: direction (observation 1089)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    280,\n    0,\n    720,\n    750\n  ]\n}"`

### 33: pilot (observation 1148)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.8725013905407906, -0.08250204342087508, 2.68797719399367, -0.150862683313207], "remaining": [1.019878788222765, -1.380958907504226e-07, 0.14887253217517493, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.0001335000000000086, 0.03267467058823528, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.035230341176470586, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.035230341176470586, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.035230341176470586, 0.0018900294117646932], [0.17932734117647053, 0.0001335000000000086, 0.035230341176470586, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151515, 151513, 151483, 151536, 151515, 151511, 151483, 151536, 151515, 151511, 151483, 151536, 151515, 151511, 151483, 151536, 151515, 151511, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.019878788222765, -1.380958907504226e-07, 0.14887253217517493, -0.0]}`

### 34: pilot (observation 1179)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [4.232302458447847, -0.08275470791113126, 2.7561978192157133, 0.11529684054954151], "remaining": [0.6600679524491312, -0.0037611306185053317, 0.08065190695313174, -0.2661595238627485]}
```

Response: `"streamed actions"`
