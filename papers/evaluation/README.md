# papers/evaluation: separating architecture capability from missing logic, and harder tasks

Reading list for docs/research/EVALUATION_20261024.md. One line per paper: what it is, and the
one mechanism we take from it.

## Method: which part limits the system?

- 2026_PRISM_oracle-perception-planning: a diagnostic benchmark with three capability tiers (basic, reasoning, long-horizon) and optional perception / memory / planning probes that can be kept, replaced or bypassed; oracle perception is the upper bound, and controlled noise degrades it (74% -> 64% with 40% of objects dropped). **Our oracle-swap design, per level, with the rest of the stack shared.**
- 2023_StructNav_training-free-semantic-frontiers: swaps ground-truth odometry, segmentation and scene graph in one at a time, with the same global planner, to find the limiting module; masks unexplored objects so the oracle is not given the answer. **One swap at a time, same downstream stack, no hidden answer.**
- 2024_OPEx_component-wise-analysis-llm-agents: splits an LLM agent into observer / planner / executor and finds perception and low-level execution to be the bottlenecks, not the LLM planner (ground-truth depth and segmentation give a very large gain). **Expect the bottleneck outside the planner; measure it.**
- 2026_CanTest_capability-oracles-vln: capability oracles that attribute a VLN failure to perception, memory, planning or decision. **A per-capability failure label for every failed flight.**
- 2022_Gervet_navigating-objects-real-world: modular (90% real) vs end-to-end (77% sim -> 23% real) object navigation; modularity transfers. Context for "architecture matters" claims.
- 2026_harness-baselines-coding-agents: report model-matched plain-agent baselines before crediting architecture; newer models improve the same scaffold a lot. **Report vanilla and handled side by side, same model, same budget.**

## Harder tasks

- 2025_EmbodiedBench_mllm-embodied-agents: 1,128 tasks in six capability subsets (commonsense, complex instruction, spatial awareness, visual perception, long-horizon); best average 28.9%. **Group tasks by capability, not by scene.**
- 2025_LH-VLN_long-horizon-vln: multi-stage navigation (3,260 tasks, ~150 steps) with subtask-level metrics (ISR, CSR, CGT). **Per-stage success and partial credit, so long tasks discriminate.**
- 2024_LoTa-Bench_task-planners: small models pass only short pick-and-place, fail on longer heat / cool tasks. **A task-length gradient (2, 3, 4 steps) exposes the planner's limit.**
- 2025_OpenFly_aerial-vln, 2025_UAV-ON_open-world-objectnav, 2025_CityNav_aerial-navigation, 2024_AeroVerse_uav-agent-benchmark: the UAV benchmarks (aerial VLN, open-world object-goal search, landmark-referenced city navigation, and five UAV task types: scene awareness, spatial reasoning, navigation exploration, task planning, motion decision). **Task families to borrow: semantic search, landmark-relative goals, spatial reasoning.** They are datasets in their own simulators; we borrow designs, not data.
