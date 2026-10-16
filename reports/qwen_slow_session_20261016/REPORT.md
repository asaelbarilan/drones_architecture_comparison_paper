# D-139: CPU placement explains a large recurring latency penalty

On this i7-14650HX / RTX 4060 Laptop host, restricting only the inference process
to performance cores repeatedly reduced first-complete-action latency. Windows
had placed the default diagnostic main thread on efficiency cores. This is a
causal within-loaded-model intervention; it does not prove every historical
slow session had the same cause or recover the earlier 0.55s on every call.

## Reversible placement experiment

Four saved contexts, one loaded model per thread-count run; one discarded warmup
per block. Each row below is the median of four calls, in actual execution order.
The model, precision, adapter, prompts and generation settings stayed fixed.

| Placement | 1 PyTorch thread | Original 16 threads |
|---|---:|---:|
| Original all cores | 1.972s | 1.750s |
| Performance cores | 0.718s | 0.865s |
| Efficiency cores | 2.082s | 1.749s |
| Performance cores again | 0.858s | 0.767s |
| Original all cores restored | 1.843s | 1.776s |

All 40 calls produced the same action tokens and decoded actions for their
respective context. Both runs restored their original process affinity. Main
thread CPU samples before/after each call support the placement, not continuous
per-thread scheduling traces. Raw results: affinity/, affinity16/, summary.json.

Earlier controls: direct/ and hidden/ each have 48 timed calls. Thread reduction
alone and hidden launch alone did not recover fast inference. Explicit process
power-throttling flags were zero. Stage/profiler data show substantial repeated
Python/PEFT/bitsandbytes dispatch; CUDA event intervals include host submission
gaps, so they are NOT GPU kernel busy-time measurements. A tiny CUDA-graph add
probe works, but is not a model graph or a model speedup result.

## Implemented bounded fix and real-worker checks

Added opt-in `cpu_placement: performance` to the spawned Windows worker. It reads
Windows CPU-set topology, intersects the highest efficiency class (performance)
with inherited allowed affinity, and records the selected mask in ready evidence.
It restores the original mask on normal/error exit. Unsupported topology or OS
fails explicitly; there is no global power/priority setting or guessed CPU list.
Generic worker defaults to `inherit`; configs/experiments/qwen_async_local.json
now opts in on this laptop. No model weights, kernel, quantization or TTL changed.

Actual worker replay includes planner, direction and monitor calls on the same
base. Seven pilot calls delivered first actions inside 1.5s; the first cold call
was 1.423s. Six warm first-action deliveries were 0.750-0.982s. This measures IPC
consumption of the first action, not completion of all eight requested actions.
Later actions still expire normally; this does not certify whole-chunk freshness.

The separate unchanged startup gate passed all three warm probes at
0.924s / 0.822s / 0.763s (limit 1.45s). Its cold warmup was cancelled at the original
expiry, which the existing gate explicitly permits. No cold-start guarantee.
Evidence: worker_performance/ and worker_gate/. One model load per worker.

75 focused CPU tests pass (placement/parser/restore, worker, expiry, async runtime,
cache and model interfaces); repository size/complexity checks and Ruff pass.
All diagnostic processes exited; GPU returned to 12 MiB and 0% utilization.
No flights, AWS, training, environment installation or freshness-limit extension.

## Interpretation and next step

This fixes a reproduced host scheduling penalty and gets warm saved-input
inference below the existing deadline. It does not establish 200ms, camera-to-action
latency, successful flight, or stable tail latency during concurrent simulator load.
Next runtime research should profile performance-core placement first, then test
fixed-shape decode/launch-overhead reductions separately. Do not compare future
optimizations against an accidentally E-core-limited baseline.

Windows defines a higher EfficiencyClass as higher performance:
https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-system_cpu_set_information

Reproduce from repository root with the GPU Python and PYTHONPATH=src:
- probe_qwen_slow_session.py --package <package> --out <new-directory>
- probe_qwen_affinity.py --package <package> --topology reports/qwen_slow_session_20261016/cpu_topology.json --threads 16 --out <new-directory>
- probe_qwen_worker_latency.py --package <package> --cpu-placement performance --gate-only --out <new-directory>
Scripts are under scripts/diagnostics/. The saved topology is specific to this
host; the worker discovers topology live and never consumes that saved file.
