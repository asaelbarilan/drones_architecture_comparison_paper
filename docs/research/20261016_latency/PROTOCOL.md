# Frozen-model latency review

Date: 2026-10-16. Scope: the existing Qwen3-VL-4B + D207 action adapter on
one RTX 4060 Laptop GPU (8 GB), without retraining or paid infrastructure.

Decisions: reduce time to the first usable four-dimensional action, keep control
responsive during inference, and choose the next measured optimization. Preserve
one base model, adapter isolation, observation age, and frozen historical profiles.

Search lanes: asynchronous VLA execution; autoregressive token decoding; small-batch
quantized inference; attention/KV/vision caching; speculative decoding; deployment
backends; inference benchmarks; negative results and numerical equivalence.
Include primary papers, official implementations and version-specific documentation.
Cover 2023–2026 plus foundational inference work. Seek at least 30 candidates,
20 substantive inspections, 15 primary papers, three direct solutions and three
benchmarks. Record unverified availability and licenses explicitly.

Exclude new training, swapping the trained pilot, extrapolating server throughput
to laptop latency, and reducing image quality without task-quality measurements.
Prior architecture research may supply directly relevant asynchronous studies;
deployment claims require fresh inspection and local measurement.

Compare: unused-token elimination/streaming, cache reuse, restricted action output
projection, optimized quantization kernels, compilation/CUDA graphs, lower visual
token budgets, and speculative decoding. Separate exact execution changes from
numerically or semantically approximate changes.

Local acceptance: existing focused tests pass; complete action tokens agree with
the original 32-token greedy output; cancellation never emits partial actions;
control remains responsive to stale/revoked requests; report actual first-action
and full-chunk latency with repeated samples. No mission-success claim from a
saved-frame inference test. Code limits: 40 lines/function excluding docstrings,
five arguments, complexity <=10, branches <=12, and <=1,000 lines/module.

Falsifiers: streaming changes action tokens; a slow worker blocks the control tick;
late/revoked actions can reach the consumer; a kernel change fails equivalence; or
speed gains disappear on changing images. Preserve failed measurements.
