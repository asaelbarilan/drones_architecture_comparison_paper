# D-163 smoke: every paper architecture flies one task (2026-10-21)

Local RTX 4060 Laptop (8 GB), one shared Qwen3-VL-4B + D207 adapter, live wall-clock runtime,
task `visible_target` ("Fly to the red pillar and stop within 2 metres"), development seed 1061,
original criteria, one flight each. Driver: `run_smoke.sh`; raw evidence in each folder.
Purpose: show that each architecture runs end to end with the intended roles. This is not a result.

| Arch | Pass | Final distance | Sim time | Model calls by role |
|---|---|---|---|---|
| C0 oracle (privileged) | yes | 1.15 m | 7.2 s | pilot 8 (classical, no model) |
| C1 LLM skills | yes | 1.63 m | 30.6 s | skill turns 3, grounding 4, pilot 9 |
| C2 VLM point | yes | 1.21 m | 26.7 s | grounding 5, pilot 9 |
| C3 + verifier | yes | 1.50 m | 21.2 s | grounding 4, pilot 8 |
| C4 + periodic monitor | yes | 1.46 m | 21.1 s | grounding 3, monitor 1, pilot 8 |
| C5 + memory | yes | 1.47 m | 21.6 s | grounding 3, monitor 1, pilot 8 |
| C6 + event recovery | yes | 1.22 m | 26.7 s | grounding 5, pilot 9 |
| FULL (D-158 stack) | yes | 1.47 m | 24.1 s | planner 1, grounding 3, monitor 1, pilot 8 |
| C7 native VLA, no shield | no | 10.20 m | 14.3 s | VLA line 1, VLA pilot 3 |
| C8 native VLA + shield | no | 10.20 m | 14.1 s | VLA line 1, VLA pilot 3 |
| C10 periodic planner -> VLA | yes | 1.46 m | 27.5 s | planner 2, grounding 3, monitor 1, VLA pilot 9 |
| C13 event planner -> VLA | yes | 1.42 m | 26.4 s | planner 1, grounding 3, monitor 1, VLA pilot 9 |

Zero collisions; all flights ended stopped; timing checks pass.

The role counts match each design:
- C0 makes no model calls.
- C2 has no planner or monitor.
- C4 and C5 add the monitor.
- C1's text-only agent uses grounding only as a tool.
- C7 and C8 use only the VLA.

C7 / C8 failure is the VLA's own decision, not a runtime fault:
- It boxed the pillar correctly (`[440, 286, 520, 500]`, centred).
- But it wrote `Left +02.6,+00.0,+00.0,+000` for a pillar about 12 m away.
- Goal memory locked that line, so the drone flew about 1.8 m and stopped inside the 1 m deadband.

This is the known weakness that goal memory locks a wrong first line, now on simulator imagery.
C8's shield did not act: there was no hazard.

GPU note: before the run, Ollama still held 2.4 GB (minicpm-v and gemma4:e2b). The user had
asked for Ollama to be closed, so both models were unloaded with `ollama stop`.
