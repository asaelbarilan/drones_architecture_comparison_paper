# Completion and step-order rules (D145)

These are runtime rules, not merely instructions to a language model.

1. A numeric step is geometrically accepted only when Euclidean position error is <= 0.5 m AND absolute heading error is <= 5 degrees.
2. Completing any step additionally requires speed <= 0.2 m/s. No extra precision is requested once these checks pass.
3. The scene monitor can return stop, continue, hold, or replan. Stop is always rejected outside the position/heading/speed checks. Hold pauses and preserves the mission; replan refreshes only the current local goal. Neither skips a step.
4. For numeric steps, a scene-clear continue cannot overrule measured completion. The scheduler advances/completes and logs numeric_completion_override with the model's original answer and measured errors. This is deliberate deterministic arbitration, not a claim that the VLM's arithmetic is reliable.
5. A stationary hold mission can finish without pilot actions. For this experiment it must also pass the unchanged independent <=0.1 m/1 degree/no-action audit.
6. Only the current ordered step can finish. An intermediate completion increments the step index exactly once; only completing the final step finishes the mission.
7. The original mission and model-authored ordered plan persist through retries. Numeric per-step changes are accumulated by code in episode-start axes. Direction output must match the committed current target; the scheduler owns final-step status.
8. Visual objectives still require a monitor stop plus arrival/stationarity; numeric arrival alone does not establish visual identity. Numeric motion following a visual step is rejected until explicit localization is provided. Visual and obstacle capability is not validated by this open-grid suite.

## Example: move, then turn

Model-authored changes: [1,0,0,0], then [0,0,0,15].
Scheduler targets: [1,0,0,0], then [1,0,0,15].
The second step cannot erase the first step's displacement or complete before the first step is accepted. These values come from the model's interpretation of the user instruction, not evaluator expected_delta fields.

The initial language interpretation can still be wrong; committing a plan does not prove arbitrary mission understanding. Final evidence includes actual model plans and all prompts.
