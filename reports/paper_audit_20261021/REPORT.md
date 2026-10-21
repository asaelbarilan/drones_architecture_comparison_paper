# Paper audit: which architectures are ready to compare (2026-10-21)

Audit only. No flights, no model calls, no config or runtime changes.
Inputs: all 107 `configs/architectures/*.yaml`, resolved through their `_base_` chains, and every
saved `manifest.json` under `runs/` and `reports/` (405 files).
Script: `scripts/audit_architectures.py`.
Full table: `architectures.md` / `architectures.json` in this folder.

The paper's question is how much planning authority a foundation model (LLM / VLM / VLA) can hold
for a single UAV, and in which architecture. It is answered by comparing the C configurations on
the same capability tasks.

## Per sentinel: real model or stand-in, and capability evidence

"Capability runs" counts the manifests on the `capability_*` tasks. The shared-Qwen live stack
writes no `manifest.json`, so its runs are listed separately, from its REPORT files.

| C | Question | Best real-model config | Model | Capability evidence | Status for the paper |
|---|---|---|---|---|---|
| C0 | Oracle ceiling (privileged) | c0_oracle | none (ground truth) | 33 runs; 6/8 (D-106) | Ready. It is a ceiling, not a competitor |
| C1 | LLM -> skills | c1_capability_gemma_dev; c1_*visual*/ordered tool variants | Gemma e2b (the original C1 used gpt-oss:20b) | 30 + 18 runs; 2/8 raw (D-106) | Real, but split across task-specific profiles; 5 of 8 tasks had no visual tools |
| C2 | VLM -> waypoint (SPF) | c2_spf_qwen4_current_dev / rgbd_arrival | Qwen3-VL-4B (Ollama) | 2 runs, one dev task only | Real, not screened on the task suite |
| C3 | C2 + verifier | c3_spf_qwen4_current_dev; c3_onfly_* | Qwen3-VL-4B / Gemma | 2 runs | Real, not screened |
| C4 | + periodic monitor | c4_onfly_gemma / qwen | Gemma / Qwen | 0 | Real config, never run |
| C5 | + keyframe memory (OnFly) | c5_capability_gemma_dev (+ hover variants) | Gemma e2b | 32 + 18 runs; 0/8 (D-106) | Real, screened; weak |
| C6 | + event-triggered recovery (PMR) | c6_pmr_qwen4_gptoss | Qwen3-VL-4B + gpt-oss:20b | 0 | Real config, never run |
| C7 | Direct VLA, no shield | c7_aerovla_native (HF AeroVLA), c7_aerovla_gemma | AeroVLA / Gemma prompt | 0 | No run; our D207 VLA not wired as C7 |
| C8 | VLA + shield | c8_aerovla_*; shared_qwen_vla_dev (D207) | AeroVLA / Qwen / **D207 VLA** | 0 manifests; grid_nav only | D207 configs exist, never run on the task suite through the harness |
| C9 | VLA + history | c9_vla_history | stand-in (mock_vla) | 0 | Stand-in only |
| C10-C13 | Reasoner -> VLA (periodic / chunked / async / triggered) | c10-c13 | stand-ins (mock / chunk VLA, simulated latency) | 0 | Stand-ins only in the harness. The shared-Qwen live stack is a real C13-like system (below) |
| C14 | World-model VLA | c14_world_model | stand-in | 0 | Stand-in only; drop or leave as future work |

## The shared-Qwen live stack (D-132 to D-158) is a real hierarchy

`src/uavlab/live_qwen/`: one Qwen3-VL-4B base serves the planner, grounding, monitor and recovery
roles; the pilot is either the trained D207 VLA adapter or a classical waypoint controller; there
is a shield; recovery is event-triggered.

- With the VLA pilot it is C13-like (event-triggered reasoner -> VLA -> shield).
- With the classical pilot it is C6-like (VLM waypoints + monitor + event recovery).
- Same `CapabilityEnv` and `capability_*.yaml` tasks as the harness. Different runtime: real
  wall-clock latency, not the SimClock's charged latency.
- Results so far, seed 1061 only:
  - classical pilot 5/9 (D-158);
  - VLA pilot about 3/9 (D-151 / D-152);
  - obstacle variants: neither pilot avoids obstacles (D-156).

## What blocks a fair comparison

1. **Model confound.** C1 = Gemma (gpt-oss originally), C2/C3 = Qwen3-VL-4B via Ollama,
   C5 = Gemma, C6 = Qwen + gpt-oss, the live stack = Qwen3-VL-4B (+ D207 adapter). Differences
   would mix the model with the architecture.
2. **Runtime / clock confound.** The harness charges a fixed latency to a simulated clock (and C1 /
   C5 charges differ, D-106). The live stack pays real latency. The same architecture would score
   differently under the two.
3. **Task-contract confound.** Several earlier profiles were task-specific: C1 tool variants per
   task; C5 hover variants; C0 has no ordered / follow behaviour. A paper cell must use one frozen
   profile per architecture across all tasks.
4. **Coverage.** C2, C3, C4, C6, C7, C8 have no task-suite screen. C9-C14 are stand-ins.
5. **Sample size.** Every capability number is a single seed (1061). The protocol needs paired
   seeds (development 1060-1064; held-out 1-40, run once at the end).

## Proposed path (decisions for the user)

- **One model everywhere:** Qwen3-VL-4B, shared base, for every LLM / VLM role, and the D207
  adapter only where a VLA pilot is the point (C7 / C8 / C13). Architecture then becomes the only
  variable. gpt-oss / Gemma results stay as historical context.
- **One runtime:** the live wall-clock runner, because the drone really waits for the model. The
  harness's SimClock stand-ins (C9-C14 mock policies) are not reportable.
- **Final matrix:**
  - architectures: C0, C1, C2/C3, C5, C6 (live classical), C8 (VLA + shield), C13 (live VLA);
  - tasks: the 9 capability tasks plus 3 obstacle tasks;
  - seeds: 3 development seeds per cell; then one frozen held-out run.
- Each missing entry first needs a one-profile port onto the shared Qwen and the live runner,
  checked on one development seed before the matrix.
