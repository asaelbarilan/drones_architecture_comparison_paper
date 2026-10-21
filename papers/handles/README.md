# What makes LLM/VLM embodied architectures work: the "handles" (D-167 reading list)

PDFs are local only (`papers/**/*.pdf` is gitignored); notes in `docs/research/HANDLES_20261022.md`.

- `2024_LLM-Modulo_llms-cant-plan-but-can-help.pdf` - Kambhampati et al., ICML 2024: LLMs cannot plan or self-verify alone; use them inside a loop with external critics. Took: verifiers as a handle (H6).
- `2026_AgentSpec_embodied-agent-scaffolds.pdf` - Chen et al. 2026: performance governed by scaffold compatibility and interaction effects, not module strength; composition can outweigh model scale. Took: the thesis framing and the add/remove-one design.
- `2024_EAI_embodied-agent-interface.pdf` - Li et al., NeurIPS 2024: module-level error taxonomy (goal interpretation, subgoal decomposition, action sequencing, transition model). Took: per-module failure attribution.
- `2022_InnerMonologue_closed-loop-feedback.pdf` - Huang et al., CoRL 2022: success detection and scene feedback back into the planner prompt. Took: evidence-based completion and feedback (H4, H7).
- `2022_ProgPrompt_program-like-prompts.pdf` - Singh et al.: program-like prompts with comments and precondition assertions. Took: typed task contracts (H1).
- `2022_SayCan_affordance-grounding.pdf` - Ahn et al.: LLM choice times affordance value. Took: feasibility checks (H6).
- `2022_CodeAsPolicies_api-programs.pdf` - Liang et al.: perception/control API and examples decide success. Took: perception hand-off as an API (H5).
- `2023_TypeFly_minispec-drone-llm.pdf` - Chen et al.: drone LLM via the MiniSpec DSL, query skill and replanning, with ablations. Took: drone-specific evidence that design choices decide success.
- `2023_CoPAL_corrective-planning.pdf` - multi-level corrective feedback during execution. Took: mid-execution recovery (H7, H8).
- `2024_Garrabe_robust-llm-task-planning-pomdp.pdf` - expected-outcomes module and feedback for small local models. Took: completion expectations per step.
- `2024_Bode_prompt-techniques-service-robots.pdf` - comparison of prompt techniques for robot task planning. Took: prompt structure as a measurable factor (H3).
- `2026_DroneServer_mcp-agentic-harness.pdf` - Ramos Silva & Burke: MCP drone harness, 98 tools, server-side state, tiered validation; 8/11 LLMs at 90-100 %. Took: harness gives cross-model reliability on drones.
- `2026_AerialClaw_llm-aerial-agent.pdf` - Li et al.: brain-skill-runtime aerial agent (our accepted C1 family). Took: the handles that made it pass in our testbed.
