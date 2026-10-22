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

**Status: supported by a 2x2 handle ablation (D-173), a stacked handle series (D-175) and a remove-one ablation of the final stack (D-180), on development seeds 1060-1062; held-out confirmation pending.**

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
| Handle ablation on FULL (D-171 v2 / D-173 v3; 3 seeds x 12 tasks, same model / runtime / tasks) | v3: FULL 21/36; + H1 24/36; + H2 21/36; + H1 and H2 27/36. H1 + H2 passes every non-planning task (24/24) and the first planning task (ordered visit 3/3). The executive alone does nothing; the pair is better than either. The remaining planning failures are perception (the 4B VLM cannot ground wall openings) and tracking | `reports/paper_handles_d172/`, D-171, D-173 |
| Final stack and remove-one ablation (D-180; 3 seeds x 12 tasks) | FULL + H1 + H2 + H5 30/36, planning 6/12 (if-then gate 3/3, ordered visit 3/3); minus H5 27/36; minus H2 21/36; minus H1 21/36 = FULL without handles 21/36. Removing either H1 or H2 returns the stack to the no-handle level; H5 only helps on top of both | `reports/paper_ablation_d179/`, D-180 |
| Live stack, same weights, no training (D-150 -> D-158) | 0/9 -> 5/9 from handle changes only: pose contract, standoff, altitude hold, object memory, stated standoff / hold, hold-as-stop | `RESEARCH_LOG.md` D-150 to D-158 |
| Live stack, numeric suite (D-143 -> D-145) | 0/4 -> 4/4 from the completion contract and ordered-step preservation only | D-143 to D-145 |
| AerialClaw C1 (D-44) | The one accepted paper family (5/5 grid, 5/5 search) had the richest handles: SOUL / BODY, soft-skill strategy, runtime checks, done / stuck verdicts, labelled metric detections | `docs/fidelity/AerialClaw.md`, D-85 |
| drone_control working loop | Handles around the models, and its recent fixes are handle fixes (S9, S10, B12): pinned reasoning order + task policy, capability allow-list, typed mission contract, proposal gate, single sequencing owner, freshness-limited blackboard | `drone_control/src/agent/` |
| Literature | LLMs cannot plan or self-verify without critics (LLM-Modulo); scaffold fit beats module strength and can outweigh model scale (AgentSpec); closed-loop feedback and typed APIs are what made LLM planners work (Inner Monologue, ProgPrompt, Code as Policies, SayCan, TypeFly); a drone harness gives 8/11 models 90-100 % mission completion (DroneServer) | `docs/research/HANDLES_20261022.md` |

Caveat: every task gave the same outcome on all three seeds (PPP or FFF) in every ablation
arm, so each arm is closer to 12 task outcomes than 36 trials. The gains are whole tasks that
flip, not noise, but the held-out seeds must show that they generalise.

What is still needed: a held-out confirmation run (the user runs it), and optionally H3, H4, H6
and H8 as separate switches.

## Finding 2 (preliminary): a VLA is a good pilot inside a hierarchy and a poor planner alone

**Status: three seeds (D-169).**
- C13 (planner -> D207 VLA pilot) is the best non-oracle stack, 22/36.
- C7 / C8 (the VLA alone, writing its own goal line) pass 0/36.
- The VLA boxes the target correctly but misjudges the distance, for example "Left +2.6 m" for
  a 12 m pillar. Goal memory locks that line (D-163).

## Finding 3 (preliminary): time-critical tasks hit a latency floor that handles cannot remove

**Status: diagnosed on three seeds (D-177 to D-179).**
- follow_target fails for every architecture, the oracle C0 included. Scoring needs tracking
  4-6 m from a marker that drives at 0.7 m/s by about t = 6.5 s. Planning (2.6 s) plus the first
  grounding (3.1 s) puts the first move at about 5.7 s, when the marker is 12 m away. After that,
  one shared 4B model serving both looks and moves gives the drone about 1.2 m per 3 s cycle,
  slower than the marker.
- closing_passage: the wall closes at t = 3 s, while the planner is still writing the plan
  (5-6 s). A model-driven stack never sees the open passage, and the hidden pillar is behind
  a corner the forward range fan cannot plan around. C0 passes it only because it is given the
  true goal.
- Three rounds of handle fixes (look while moving, two wall detours, path progress) did not move
  either task. They are kept as measured negatives (FULL_H1257, FULL_H125D).

## Open items

- H5 is built and in the final stack (D-174 / D-175); H7 and the wall detour are negatives.
- Optional: H3, H4, H6, H8 as separate switches.
- Held-out evaluation: once, at the end.
