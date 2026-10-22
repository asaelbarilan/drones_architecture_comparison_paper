# DRAFT v0 (2026-10-22) - working title

**Diagrams Don't Fly: Handles, Not Architecture Families, Decide Whether Small Foundation Models
Can Plan for a Drone**

Status: v0, structure and argument. Numbers marked [TBD] wait for the full D-166 matrix (three
seeds) and the handle ablation (not built yet). Findings and their evidence are tracked in
`docs/RESEARCH.md`. Nothing here is a claim until it appears there with evidence.

---

## Abstract (draft)

Foundation-model autonomy for drones is usually described by its architecture family. The
families are:
- an LLM that calls skills;
- a VLM that points to waypoints;
- a vision-language-action (VLA) model that flies directly;
- hierarchies that combine them.

We ask whether the family decides success. We build twelve such architectures as configurations
of one runtime, with the same small on-board model (Qwen3-VL-4B, plus a trained 4B VLA adapter),
the same real-time loop, the same path planner and safety shield, and the same twelve capability
tasks. Built only from their diagram's modules, every model-driven architecture solves simple
see-and-go missions and fails every task that needs planning: a conditional branch, an ordered
visit, recovery from a closed passage, following a moving target [TBD: three-seed numbers].

The same model improves from 0/9 to 5/9 when only the connective logic changes. That logic
includes typed task contracts, a single owner of mission sequencing, evidence-based completion,
and the perception-to-state hand-off. We call this logic the system's *handles*. [TBD: handle
ablation result.]

We argue that the handles, not the architecture family, determine whether a small foundation
model can plan for a drone. Architecture comparisons should report them as first-class factors.

## 1 Introduction (draft)

- Drone autonomy papers present systems as boxes: planner, perception, executor, monitor.
  Comparisons between families are made across different models, simulators, sensors and
  prompts, so a difference in success cannot be attributed to the family.
- We remove those confounds. One model, one runtime and one task suite run all families as
  configurations; only the architecture switches change.
- The first result is negative and, we think, important. The diagram alone does not plan: every
  vanilla configuration fails the planning tasks.
- The working systems we and others built (AerialClaw, our drone_control stack, and our own live
  stack after repair) all work because of logic outside the diagram. This matches the scaffold
  literature (LLM-Modulo, AgentSpec, Inner Monologue, ProgPrompt, SayCan, TypeFly).
- Contributions:
  1. a controlled testbed where architecture families are configurations of one runtime and one
     model;
  2. a twelve-architecture by twelve-task evaluation with paired seeds, an oracle ceiling and a
     cost vector;
  3. a taxonomy of handles (H1-H8) with controlled add-one / remove-one ablations [TBD];
  4. evidence that a trained VLA is a good pilot inside a hierarchy and a poor planner alone.

## 2 Related work (outline)

- **Architecture families for LLM/VLM drones.** TypeFly, AerialClaw, See-Point-Fly, OnFly,
  PMR / Selective Agentic Recovery, CognitiveDrone (-R1), FLIGHT, AeroVLA. Source:
  `docs/research/*`, the 94-paper UAV survey.
- **Scaffolds and handles.** LLM-Modulo, AgentSpec, Embodied Agent Interface, Inner Monologue,
  ProgPrompt, Code as Policies, SayCan, CoPAL, the DroneServer MCP harness. Source:
  `docs/research/HANDLES_20261022.md`.
- **Benchmarks.** AerialVLN, UAV-Flow, CognitiveDrone. The gap: no architecture comparison under
  identical constraints (survey Table 8).

## 3 Testbed (draft, from D-159 - D-166)

- **One model.** Qwen3-VL-4B (NF4) serves every language / vision role. The D207 LoRA adapter
  (trained on UAV-Flow, 70.3 % on its test set) serves VLA pilot roles. One GPU owner; calls
  are serialized.
- **One runtime.** A wall-clock 20 Hz control loop. Model latency is paid, not simulated. Actions
  expire. All roles share the asynchronous scheduler.
- **Shared execution.**
  - SUPER local path planning on the range fan, with the same parameters as the oracle ceiling;
  - a velocity controller;
  - a collision shield, except C7 (no shield by definition).
- **Tasks.** Twelve capability tasks in a rendered 3-D grid simulator with an independent
  evaluator that no model sees:
  - basic: coordinate, visible target, approach-and-hover;
  - perception: search, the overturned vehicle among two;
  - planning: conditional gate, ordered visit, closing passage, follow;
  - obstacles: post, slalom, low wall.
- **Protocol.** Development seeds 1060-1062 for every reported matrix. Held-out seeds run once.
  No per-task tuning, no retries.

## 4 Architectures as configurations (draft table)

| ID | Who decides the goal | Pilot | Verifier | Monitor | Recovery | Memory |
|---|---|---|---|---|---|---|
| C0 | evaluator goal (privileged ceiling) | classical | yes | - | - | - |
| C1 | text-only LLM picks one skill per turn | classical | yes | - | - | skill history |
| C2 | VLM points in the image | classical | - | - | - | - |
| C3 | as C2 | classical | yes | - | - | - |
| C4 | as C2 | classical | yes | periodic | - | - |
| C5 | as C2 | classical | yes | periodic | - | yes |
| C6 | as C2 | classical | yes | - | event | - |
| FULL | LLM plans steps, VLM grounds them | classical | yes | arrival + periodic | event | yes |
| C7 | the VLA writes its own goal line | VLA | - | - | - | goal memory |
| C8 | as C7 | VLA + shield | yes | - | - | goal memory |
| C10 | as FULL, planner on a period | VLA | yes | yes | periodic | yes |
| C13 | as FULL, planner on events | VLA | yes | yes | event | yes |

## 5 Results (to fill)

- **5.1 Vanilla matrix** (432 flights, seeds 1060-1062, zero collisions; D-169). Passes / 36:
  C0 28; C13 22; FULL 21; C5 and C6 18; C10 16; C3 and C4 15; C2 12; C1 9; C7 and C8 0.
  Planning tasks: 0/12 for every model-driven architecture (C0 4/12). Tables:
  `reports/paper_matrix_d165/tables.md`.
- **5.2 The same model, different handles.** The history D-143 -> D-145 (0/4 -> 4/4) and
  D-150 -> D-158 (0/9 -> 5/9).
- **5.3 Handle ablation** (FULL base, 3 seeds; D-171 v2, D-173 v3). v3: FULL 21/36; + H1 24/36;
  + H2 21/36; + H1 and H2 27/36, with planning 0/12 -> 3/12 (ordered visit 3/3) and every
  non-planning task passed. The executive alone does nothing; the pair is better than either.
  Remaining failures: wall openings cannot be grounded by the 4B VLM, and tracking.
- **5.4 VLA alone vs in a hierarchy.** [TBD]

## 6 Discussion (outline)

- **Why vanilla fails planning.** Per-module failure attribution, in the Embodied Agent Interface
  style:
  - goal interpretation (the branch flattened in conditional_gate);
  - state tracking (the second target lost in ordered_visit);
  - recovery (no route when the passage closes);
  - missing behaviour (no tracking skill).
- The taxonomy H1-H8 and what each fixes.
- Implications for comparing published systems: report the handles.

## 7 Limitations (outline)

- A synthetic rendered simulator, not AirSim or real flight.
- One model family, at 4B.
- Development seeds only, until the final held-out run.
- The handles are partly designed by us. We mitigate this by using only public mission text
  and sensed state, never evaluator truth.
