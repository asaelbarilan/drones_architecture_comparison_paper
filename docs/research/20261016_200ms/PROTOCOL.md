# Frozen VLA: 200 ms first-action research protocol

Search date: 2026-10-16. Decision: can the installed Qwen3-VL-4B NF4 plus D207
adapter on Windows RTX4060 Laptop8GB reduce capture-to-first-complete-action
latency from approximately550ms to200ms without training or weaker freshness?
No implementation, model download, GPU experiment, flight or cloud use in this review.

Primary outcome: four valid autoregressive action tokens decoded and delivered,
including preprocessing, transfer and IPC. Controller frequency and action-chunk
throughput are separate metrics. Preserve trained inputs and checkpoint semantics;
approximate quantization/pruning requires a separately labelled quality comparison.

Search lanes: exact VLA acceleration; autoregressive action decoding; CUDA graphs,
compile and quantized kernels; mixed precision/SDPA; head projection; visual/KV
reuse; draft-free speculation; UAV/robot latency benchmarks and failure evidence.
Terms include Qwen3-VL, PEFT vision LoRA, NF4, static KV, Marlin, TorchAO, AWQ,
GPTQ, FlashAttention, VLA-Cache, FastV, CogVLA, EfficientVLA and speculative actions.
Date range2022–2026 plus foundational dependencies. Search official papers,
author repositories and library documentation, follow cited mechanisms backward.

Use the existing30-candidate D134 ledger as a starting bibliography, preserving
its provenance rather than pretending it is a new inspection. Reopen central
sources and inspect their implementation resources; add hardware/runtime sources.
Stop after at least30 screened works and20 substantively inspected relevant works,
including15 primary papers and direct-solution/benchmark coverage. Record unavailable
full text, licenses, weights and Windows compatibility explicitly, never guess.

Compare reuse/adaptation/requantization/retraining; exclude retraining from the
recommended route. Do not multiply unrelated published speedups or transfer A100
throughput numbers to laptop first-action latency. Central claims must be supported
by full text or official implementation; validation schema is not a truth audit.

Deliver protocol/search log, evidence JSON/table, resource inventory, mechanism
taxonomy, ranked options, falsification tests and an uncertainty-aware200ms plan.
