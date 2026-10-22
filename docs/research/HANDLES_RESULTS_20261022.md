# Handles: results so far (D-168 to D-176, 2026-10-22)

Companion to the research note (in the PDF it follows this section). All runs use the same model (Qwen3-VL-4B + D207 adapter),
the same real-time runtime, the same 12 tasks and development seeds 1060-1062. Each variant
was flown 36 times. These are development results; the held-out run comes at the end.

## The handles built so far

| Handle | What it is | What it changes |
|---|---|---|
| H1 typed task contract | The planner writes a small typed program (visit, pass, condition, follow, goto, search) instead of plain text steps | What the planner hands over |
| H2 kind-aware executive | One owner runs that program: asks the camera at a branch, flies through openings, follows for the stated time, advances only on evidence | Who runs the plan, and how |
| H5 measured openings | Gaps in walls measured by the drone's range sensor, given to checks and fly-through steps; questions the sensor can answer are routed to it | How perception reaches the plan |
| H7 look while following | A follow step looks again while moving instead of stopping each time | Timing of perception during tracking |

None of these adds a box to the architecture diagram. They change the logic between the boxes.

## Step 1: H1 and H2, alone and together (FULL stack as base)

| Variant | Passes / 36 | Planning tasks / 12 |
|---|---|---|
| FULL (no handles) | 21 | 0 |
| + H1 only | 24 | 0 |
| + H2 only | 21 | 0 |
| + H1 and H2 | 27 | 3 (ordered visit 3/3) |

Neither handle helps planning alone. A typed plan that nobody executes is inert, and an
executive with nothing typed to execute does nothing. Together they solve the first planning
task. This matches the scaffold literature: interaction between components matters more than
any single module.

How the version-1 handles failed is evidence too. The planner wrote a correct if-then program,
and a strict validator rejected it for one extra field. Fixing the connecting logic, not the
model, is what moved the score:

| Version | H1 + H2 |
|---|---|
| v1 | 18/36 |
| v2 | 26/36 |
| v3 | 27/36 |

## Step 2: adding H5 (measured openings) on top of H1 + H2

| Variant | Passes / 36 | Planning / 12 | What changed |
|---|---|---|---|
| H1 + H2 | 27 | 3 | - |
| + H5 (facts given to the model) | 28 | 4 | the gate is reached every time, but the right branch only 1/3 |
| + H5 with check routing | 30 | 6 (gate 3/3, ordered visit 3/3) | sensor-answerable questions answered by the sensor |

The small model ignored the correct measured facts in its answer: it said "no left opening"
when the sensor measured one. Routing the question to the sensor fixed it on every seed. This is
another connecting-logic decision, not a better model.

## Step 3: still open

- **Follow target (0/3).** The first look-while-moving version starved the pilot of GPU time, so
  the drone never moved. Fixed to "move first, look while moving"; being flown now.
- **Closing passage (0/3).** The target is hidden behind the wall that closed. A wall-end detour
  (fly past the measured wall end, then look again) is being flown now.

## Where this stands

| Configuration | Passes / 36 | Planning / 12 |
|---|---|---|
| Best vanilla architecture (C13) | 22 | 0 |
| FULL | 21 | 0 |
| FULL + H1 + H2 + H5 | 30 | 6 |

Same model, same tasks, same seeds. The difference is only the handles.

After the stack works, a remove-one ablation will measure each handle's contribution: the full
stack minus one handle at a time.
