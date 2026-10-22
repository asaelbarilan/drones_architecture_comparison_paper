# papers/forecasts: predicting outcomes at each level of a hierarchy

Reading list for docs/research/FORECASTS_20261022.md. One line per paper: what it is, and the
one mechanism we take from it.

- 2023_DoReMi_plan-execution-misalignment: the LLM writes constraints for each skill and a VLM checks them during execution; a violation replans at once. **Our forecast-mismatch handle.**
- 2025_CodeAsMonitor_reactive-proactive-failure-detection: the VLM writes code that checks spatio-temporal constraints on compact geometric elements in real time, reactively (after a failure) and proactively (before one). **Make forecasts measurable quantities checked by code, not by the model.**
- 2025_Stechly_self-verification-limitations: self-critique by the same LLM collapses accuracy (graph colouring 16% to 2%); a sound external verifier raises it (to 38%). **The forecast must be checked by the sensor or code, never by the same model.**
- 2023_Valmeekam_self-critiquing-plans: LLM plan verifiers give many false positives. Same lesson for plan checking.
- 2024_Xiong_llm-uncertainty-calibration: verbalised confidence is overconfident; consistency across samples is better. **Ask for a checkable number, not a confidence.**
- 2023_KnowNo_robots-ask-for-help-conformal: conformal prediction over the planner's options gives calibrated uncertainty. A later option if we want calibrated planner confidence.
- 2024_EAI_embodied-agent-interface: scores LLMs per module (goal interpretation, subgoal decomposition, action sequencing, transition modelling); final success hides where models fail. **The per-level scoring frame for paper conclusion 2.**
- 2023_LLM-DP_dynamic-planning: planning needs a model of the effects of actions and a check of whether the state meets the goal; the LLM is paired with a symbolic planner. Precedent for expected effects.
- 2025_GVL_vlm-in-context-value-learners: a VLM estimates task progress by ordering shuffled frames, usable as a success detector. Progress forecast for the monitor level.
- 2023_Du_vlm-success-detectors: success detection as visual question answering (SuccessVQA); generalisation is the hard part.
- 2019_Ma_self-monitoring-progress-estimation: a VLN agent predicts its own progress toward the goal, and the progress monitor improves success by 8 points. Early evidence that predicting progress helps navigation.
- 2023_REFLECT_failure-explanation-correction: a hierarchical summary of sensed experience lets an LLM explain and correct failures. Useful for explaining a forecast mismatch.
- 2025_CoT-VLA_visual-chain-of-thought: the VLA predicts a future subgoal image, then the actions to reach it (+17% real). The VLA-level forecast; ours (D207) already predicts the next box and remaining motion.
- 2023_Dreamwalker_mental-planning-vln and 2021_Pathdreamer_world-model-navigation: a world model imagines future views before acting. Pathdreamer looking ahead gives about half the gain of seeing real views. **Out of scope here: too slow for a 4B on-board loop (see the latency floor, D-177).**
