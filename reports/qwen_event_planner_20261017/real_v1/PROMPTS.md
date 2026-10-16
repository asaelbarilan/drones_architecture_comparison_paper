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
Evaluate the active VISUAL objective, not the short waypoint.
Return ONLY JSON with status and reason, reason at most 15 words.
A waypoint is a short movement checkpoint. waypoint_reached NEVER proves
the object was reached. Ignore it when deciding mission completion.
stop ONLY if object_evidence_fresh AND object_near AND stationary are true
AND the requested object remains visible in the current camera.
If the object is visible but far or its range is unknown, return continue.
If identity is lost or the scene changed, return replan. If unsafe, return hold.
Never infer object range from waypoint position error or apparent size alone.
Context: 
```

## planner_recovery template

```text
You are the event-driven mission planner. Preserve the original mission,
ordered committed steps and completed steps. A local waypoint is not a subgoal.
Review the trigger and observation memory. Choose exactly one action:
retry_current (retry the same objective), refresh_view (request fresh visual
grounding for that same objective), hold (temporary stationary safety pause).
Do not invent motion, skip steps, change target identity or claim completion.
Return JSON with exactly action and reason. Reason at most 15 words.
Use refresh_view for a lost target or stale perception, retry_current for
recoverable stalled progress, hold for unsafe or unresolved conflicting evidence.
Context: 
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

### 5: direction (observation 80)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    500,\n    300\n  ]\n}"`

### 6: pilot (observation 137)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.0, 0.0, 0.0, -0.0], "remaining": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, 0.1924040823529412, -0.003860441176470608]], "tokens": [151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485, 151560, 151516, 151387, 151485], "remaining_supplied": [1.0648875569308056, -0.1, 0.5966694990477901, -5.364720867281331]}`

### 7: pilot (observation 168)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.015294520750305414, -0.0031409074251095236, 0.1807070499103638, -0.29604267897788494], "remaining": [1.0500794865940921, -0.09143466108276405, 0.4159624491374263, -5.068678188303447]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608], [0.016286588235294053, -0.010269688235294117, 0.1924040823529412, -0.003860441176470608]], "tokens": [151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485, 151560, 151518, 151387, 151485], "remaining_supplied": [1.0500794865940921, -0.09143466108276405, 0.4159624491374263, -5.068678188303447]}`

### 8: pilot (observation 199)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.055869892103526046, -0.02634189856317877, 0.662075565990746, -0.8641672045884786], "remaining": [1.0100138102993754, -0.058431728070549666, -0.06540606694295592, -4.500553662692853]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.016286588235294053, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485, 151560, 151516, 151539, 151485], "remaining_supplied": [1.0100138102993754, -0.058431728070549666, -0.06540606694295592, -4.500553662692853]}`

### 9: pilot (observation 230)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.09762862133836417, -0.03886569172473673, 0.7516492714744896, -1.4311688965809737], "remaining": [0.9684840911155999, -0.036956966700584515, -0.15497977242669947, -3.933551970700358]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485], "remaining_supplied": [0.9684840911155999, -0.036956966700584515, -0.15497977242669947, -3.933551970700358]}`

### 10: pilot (observation 261)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.29643891933509275, -0.052899270178252286, 0.7509635925894655, -1.9982494638528583], "remaining": [0.7696236920548549, -0.02027708066518427, -0.15429409354167545, -3.366471403428473]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608], [0.09101360000000003, -0.0033342294117646998, -0.0005490470588235263, -0.003860441176470608]], "tokens": [151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485, 151549, 151516, 151539, 151485], "remaining_supplied": [0.7696236920548549, -0.02027708066518427, -0.15429409354167545, -3.366471403428473]}`

### 11: pilot (observation 292)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.5295801665074292, -0.06993740428355395, 0.7495584492150931, -2.56567251705456], "remaining": [0.5361165176877051, -0.0060697088483955, -0.15288895016730297, -2.7990483502267716]}
```

Response: `"streamed actions"`

### 12: direction (observation 305)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    433,\n    0,\n    600,\n    380\n  ]\n}"`

### 13: pilot (observation 361)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.6367448650204564, -0.07850397024832287, 0.7489103727729751, -2.7225761508339676], "remaining": [1.0201789401994583, 0.03322159320209203, 0.5172906639413584, 1.7342260089081099]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.1924040823529412, 0.0018900294117646932]], "tokens": [151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483, 151542, 151513, 151387, 151483], "remaining_supplied": [1.0201789401994583, 0.03322159320209203, 0.5172906639413584, 1.7342260089081099]}`

### 14: pilot (observation 392)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [0.9152908892240639, -0.07721173537416207, 1.1351727205684172, -2.4559396064004697], "remaining": [0.7420876981378054, 0.015246605002410235, 0.13102831614591626, 1.4675894644746117]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7420876981378054, 0.015246605002410235, 0.13102831614591626, 1.4675894644746117]}`

### 15: direction (observation 419)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    400\n  ]\n}"`

### 16: pilot (observation 476)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.2578766765679164, -0.07496903752281237, 1.2227958298745225, -2.248711322964316], "remaining": [1.002378197857726, -0.002442490424835686, 0.49604786607490237, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, -0.0033342294117646998, 0.1924040823529412, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.1924040823529412, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.1924040823529412, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.1924040823529412, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.1924040823529412, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.1924040823529412, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151516, 151387, 151483, 151541, 151516, 151387, 151483, 151541, 151516, 151387, 151483, 151541, 151516, 151387, 151483, 151541, 151516, 151387, 151483, 151541, 151516, 151387, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [1.002378197857726, -0.002442490424835686, 0.49604786607490237, -0.0]}`

### 17: pilot (observation 507)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.5491440032402277, -0.09275628152366483, 1.608934663899955, -1.982505580627214], "remaining": [0.7106477078526431, 0.0006007310663364296, 0.10990903204946978, -0.26620574233710165]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, 0.028841164705882355, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151541, 151513, 151516, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7106477078526431, 0.0006007310663364296, 0.10990903204946978, -0.26620574233710165]}`

### 18: direction (observation 531)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    400,\n    0,\n    600,\n    500\n  ]\n}"`

### 19: pilot (observation 586)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [1.8500913057005774, -0.0932600630046469, 1.7434582748412062, -1.8080683951120347], "remaining": [0.9936187240400405, -0.002285927139055288, 0.3857227608001086, -0.0]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, -0.0033342294117646998, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.10039994117647061, 0.0018900294117646932], [0.14536051764705893, -0.0033342294117646998, 0.10039994117647061, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151516, 151460, 151483, 151541, 151516, 151460, 151483, 151541, 151516, 151460, 151483, 151541, 151516, 151460, 151483, 151541, 151516, 151460, 151483, 151541, 151516, 151460, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.9936187240400405, -0.002285927139055288, 0.3857227608001086, -0.0]}`

### 20: pilot (observation 617)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.1411669414781827, -0.108789436715366, 1.9447317915036084, -1.5414796068809788], "remaining": [0.7022092833278353, 0.0007845836183896227, 0.18444924413770636, -0.2665887882310558]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.1385671529411765, 0.00706895882352937, 0.08251024705882354, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, 0.01989631764705882, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151542, 151513, 151474, 151483, 151542, 151513, 151523, 151483, 151542, 151513, 151539, 151483, 151542, 151513, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.7022092833278353, 0.0007845836183896227, 0.18444924413770636, -0.2665887882310558]}`

### 21: direction (observation 640)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    380,\n    0,\n    650,\n    530\n  ]\n}"`

### 22: pilot (observation 698)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.4320309181435866, -0.10672997565099518, 2.0859892538402036, -1.3669942103423969], "remaining": [0.9846737891682574, 0.027324490041096133, 0.3503027344762826, 1.6492522851130313]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.007640499999999939], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.007640499999999939], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.007640499999999939], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.007640499999999939], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.007640499999999939], [0.14536051764705893, 0.003601229411764717, 0.10039994117647061, 0.007640499999999939], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151514, 151460, 151481, 151541, 151514, 151460, 151481, 151541, 151514, 151460, 151481, 151541, 151514, 151460, 151481, 151541, 151514, 151460, 151481, 151541, 151514, 151460, 151481, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.9846737891682574, 0.027324490041096133, 0.3503027344762826, 1.6492522851130313]}`

### 23: pilot (observation 729)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [2.7236010482931152, -0.10506436035095945, 2.287317160994564, -0.28901718400770965], "remaining": [0.693455559476899, 0.005658494274763004, 0.14897482732192202, 0.5712752587783443]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.14536051764705893, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.1385671529411765, 0.00706895882352937, -0.0005490470588235263, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151541, 151513, 151539, 151483, 151542, 151513, 151539, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.693455559476899, 0.005658494274763004, 0.14897482732192202, 0.5712752587783443]}`

### 24: direction (observation 751)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    333,\n    0,\n    666,\n    600\n  ]\n}"`

### 25: pilot (observation 810)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.0101503236637837, -0.09456909645057021, 2.332996002699387, -0.12584914111850462], "remaining": [0.9754727004659082, -0.004718631939874013, 0.29687711241089687, -0.11072302708444808]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.9754727004659082, -0.004718631939874013, 0.29687711241089687, -0.11072302708444808]}`

### 26: pilot (observation 841)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.369649336552377, -0.09531339825672491, 2.498402700526995, -0.26495294661591756], "remaining": [0.6159826706081025, -0.003268480778702315, 0.13147041458328879, 0.028380778412964887]}
```

Response: `"streamed actions"`

### 27: direction (observation 856)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    333,\n    0,\n    666,\n    666\n  ]\n}"`

### 28: pilot (observation 912)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.570458683063123, -0.09598830918223855, 2.5600782670589908, -0.17752067463241958], "remaining": [0.9813106787788803, -0.0019781314994452015, 0.22105012761026455, -0.11143246827261438]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.17932734117647053, 0.0001335000000000086, 0.08251024705882354, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151536, 151515, 151474, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.9813106787788803, -0.0019781314994452015, 0.22105012761026455, -0.11143246827261438]}`

### 29: pilot (observation 943)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [3.9300966083027467, -0.09705731075427204, 2.72555024301023, -0.31634334581829915], "remaining": [0.6216742453938294, -0.0005171473210050237, 0.055578151659025465, 0.027390202913265195]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.14536051764705893, 0.0001335000000000086, 0.03139683529411766, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.03139683529411766, -0.0009852058823529575], [0.14536051764705893, 0.0001335000000000086, 0.03139683529411766, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151541, 151515, 151514, 151484, 151541, 151515, 151514, 151484, 151541, 151515, 151514, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.6216742453938294, -0.0005171473210050237, 0.055578151659025465, 0.027390202913265195]}`

### 30: direction (observation 958)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    275,\n    0,\n    775,\n    800\n  ]\n}"`

### 31: pilot (observation 1014)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [4.130108669089714, -0.09790959751073158, 2.7888742932123076, -0.36200553248130707], "remaining": [0.961423910642337, 0.04990152914365137, 0.08565287485256956, 2.8202533410059036]}
```

Response: `{"steps_fru_m_yaw_rad": [[0.17932734117647053, 0.00706895882352937, 0.03139683529411766, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, 0.03139683529411766, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, 0.03139683529411766, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, 0.03139683529411766, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, 0.03139683529411766, 0.0018900294117646932], [0.17932734117647053, 0.00706895882352937, 0.03139683529411766, 0.0018900294117646932], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575], [0.0026998588235294108, 0.0001335000000000086, -0.0005490470588235263, -0.0009852058823529575]], "tokens": [151536, 151513, 151514, 151483, 151536, 151513, 151514, 151483, 151536, 151513, 151514, 151483, 151536, 151513, 151514, 151483, 151536, 151513, 151514, 151483, 151536, 151513, 151514, 151483, 151562, 151515, 151539, 151484, 151562, 151515, 151539, 151484], "remaining_supplied": [0.961423910642337, 0.04990152914365137, 0.08565287485256956, 2.8202533410059036]}`

### 32: pilot (observation 1045)

```text
{"instruction": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "box": null, "state": [4.489928368022978, -0.08557488239790989, 2.851860723059678, -0.09557211975875247], "remaining": [0.6018469406488688, 0.03249535540228232, 0.022666445005198987, 2.5538199282833487]}
```

Response: `"streamed actions"`

### 33: direction (observation 1060)

```text
Locate the requested object in this image, including partially cropped objects.
Return ONLY JSON with keys target_visible (boolean) and box
([left,top,right,bottom] integers normalized to 0..1000, or null if absent).
Use the visible object bounds. Do not return a navigation action or example values.
Requested object context: {"active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "authorized_target": "red pillar", "numeric_target": false}
```

Response: `"{\n  \"target_visible\": true,\n  \"box\": [\n    175,\n    0,\n    825,\n    980\n  ]\n}"`

### 34: monitor (observation 1120)

```text
Evaluate the active VISUAL objective, not the short waypoint.
Return ONLY JSON with status and reason, reason at most 15 words.
A waypoint is a short movement checkpoint. waypoint_reached NEVER proves
the object was reached. Ignore it when deciding mission completion.
stop ONLY if object_evidence_fresh AND object_near AND stationary are true
AND the requested object remains visible in the current camera.
If the object is visible but far or its range is unknown, return continue.
If identity is lost or the scene changed, return replan. If unsafe, return hold.
Never infer object range from waypoint position error or apparent size alone.
Context: {"original_mission": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "active_objective": "Find the red pillar in the camera view and approach it. Stop nearby while keeping the red pillar visible. Do not approach other colored objects.", "target_identity": "red pillar", "active_step": 0, "waypoint_reached": true, "object_evidence_fresh": true, "object_range_m": 1.3630176224024337, "object_near": true, "required_object_range_m": 1.5, "stationary": true, "trigger": "fresh object proximity; verify visual accomplishment"}
```

Response: `"{\"status\": \"stop\", \"reason\": \"Red pillar visible, stationary, near target range\"}"`
