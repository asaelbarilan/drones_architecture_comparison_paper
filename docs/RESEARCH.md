# Research findings for the paper (planning capability of LLM/VLM/VLA drone architectures)

This is research documentation, **not the paper**. It holds the findings the paper will argue,
each with its evidence and status. Decisions and their rationale stay in `RESEARCH_LOG.md`;
literature notes stay in `docs/research/`. The paper draft lives in `docs/paper/DRAFT.md`.

## Research question

How much planning authority can a foundation model (LLM, VLM or VLA) hold for a single UAV, and
what makes such an architecture work, across task types (basic, perception, planning,
obstacles)?

Setup (D-159 - D-166):
- One shared model: Qwen3-VL-4B, plus the D207 VLA adapter for VLA pilots.
- One real wall-clock runtime.
- One shared SUPER path planner and shield.
- Twelve architecture configurations (C0 - C13).
- Twelve capability tasks.
- Paired development seeds; held-out seeds untouched.

## Finding 1 (working thesis): vanilla architectures do not work by themselves; the handles do

**Status: supported by converging evidence; not yet measured by a controlled handle ablation.**

The textbook architectures differ in which modules exist and who decides the goal: skills,
waypoints, direct VLA, hierarchy. Built from those modules alone, they solve simple
see-and-go tasks and fail the planning tasks. What made systems work, in our hands and in the
literature, is the logic that connects the modules (the "handles"):
- typed task contracts;
- a single sequencing owner;
- the pinned reasoning order of prompts;
- evidence-based completion;
- the perception-to-state hand-off;
- feasibility critics;
- outcome feedback;
- recovery invocation policy.

| Evidence | What it shows | Source |
|---|---|---|
| D-166 matrix, complete (12 archs x 12 tasks x 3 seeds = 432 flights, one model and runtime, zero collisions) | Every model-driven configuration passes 0/12 planning tasks (if-then gate, ordered visit, closing passage, follow); oracle 28/36 overall. Best non-oracle C13 22/36 and FULL 21/36; vanilla C1-C6 9-18/36; VLA alone 0/36 | `reports/paper_matrix_d165/tables.md`, D-169 |
| Live stack, same weights, no training (D-150 -> D-158) | 0/9 -> 5/9 from handle changes only: pose contract, standoff, altitude hold, object memory, stated standoff / hold, hold-as-stop | `RESEARCH_LOG.md` D-150 to D-158 |
| Live stack, numeric suite (D-143 -> D-145) | 0/4 -> 4/4 from the completion contract and ordered-step preservation only | D-143 to D-145 |
| AerialClaw C1 (D-44) | The one accepted paper family (5/5 grid, 5/5 search) had the richest handles: SOUL / BODY, soft-skill strategy, runtime checks, done / stuck verdicts, labelled metric detections | `docs/fidelity/AerialClaw.md`, D-85 |
| drone_control working loop | Handles around the models, and its recent fixes are handle fixes (S9, S10, B12): pinned reasoning order + task policy, capability allow-list, typed mission contract, proposal gate, single sequencing owner, freshness-limited blackboard | `drone_control/src/agent/` |
| Literature | LLMs cannot plan or self-verify without critics (LLM-Modulo); scaffold fit beats module strength and can outweigh model scale (AgentSpec); closed-loop feedback and typed APIs are what made LLM planners work (Inner Monologue, ProgPrompt, Code as Policies, SayCan, TypeFly); a drone harness gives 8/11 models 90-100 % mission completion (DroneServer) | `docs/research/HANDLES_20261022.md` |

What is still needed to state it as a result: an add-one / remove-one handle ablation on the same
tasks and seeds (the taxonomy H1 - H8 is in the research note).

## Finding 2 (preliminary): a VLA is a good pilot inside a hierarchy and a poor planner alone

**Status: three seeds (D-169).**
- C13 (planner -> D207 VLA pilot) is the best non-oracle stack, 22/36.
- C7 / C8 (the VLA alone, writing its own goal line) pass 0/36.
- The VLA boxes the target correctly but misjudges the distance, for example "Left +2.6 m" for
  a 12 m pillar. Goal memory locks that line (D-163).

## Open items

- Handle ablation H1 / H2 on FULL (D-168, running).
- Handle ablation design and implementation.
- Held-out evaluation: once, at the end.
