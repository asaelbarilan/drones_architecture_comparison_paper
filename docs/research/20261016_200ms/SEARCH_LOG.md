# Search and inspection log — 2026-10-16

Protocol written before searches. Starting bibliography: ../20261016_latency/evidence.json,
30 candidates with prior inspection provenance. This is an update, not 30 new readings.

Searches: `VLA inference acceleration training free Qwen VLA cache FastV EfficientVLA latency`;
`Qwen3 VL torch compile static cache NF4 inference latency flash attention float32`.
Followed author papers to official Qwen, Marlin, FlashAttention and Transformers resources.
Followed speculative decoding to its ICML/PMLR PDF after arXiv HTML failed.

Fresh central inspection: EfficientVLA methods/results; VLA-Cache platform/results;
SpecPrune methods and sections 7/10; AWQ calibration/multimodal results;
Marlin repository requirements/packing; Transformers4.57.3 inference optimizations;
PyTorch2.6 SDPA restrictions/numerics; Qwen FlashAttention guidance; FlashAttention
Windows/Ada requirements; FastV methods/results; speculative decoding algorithm and
TPU experiments; vla.cpp project methods, latency table and release status.
Other opened inherited papers (GPTQ, PagedAttention, SGLang, FlashAttention2) retain
prior inspection provenance; reopening metadata alone is not a new methods reading.
QLoRA HTML unavailable; its row remains abstract-only. FastVLA remains abstract-only.

Fresh resource negatives: vla.cpp says code/paper coming soon; no verified Qwen D207
implementation. FlashAttention explicitly warns Windows compilation needs testing.
FlashRT NVFP4 Qwen example surfaced on RTX5090; not transferred to Ada4060.
Learned selectors/new flow or parallel action heads excluded under no retraining.
No independent benchmark found for our exact hardware/model/adapter/first-quartet metric.

Local checks: D136 saved timing JSON, instrumented profile tables, shared_qwen loader,
packaged qwen_backend and trainer setup, installed PEFT preparation source. No GPU
inference, simulator flight, model download or cloud call performed.
Resource licenses not verified remain open; no software adoption decision is made.
