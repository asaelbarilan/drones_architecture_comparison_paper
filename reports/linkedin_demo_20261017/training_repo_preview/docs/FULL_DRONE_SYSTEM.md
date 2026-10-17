# Full drone system: training, model and architecture

The project has three connected parts. Keep one canonical copy of each rather than duplicating runtime code across repositories.

| Part | Canonical location | Contains |
|---|---|---|
| VLA training | [drone_small_vla_training](https://github.com/asaelbarilan/drone_small_vla_training) | Data preparation, supervised training, action codec, research and evaluation history |
| Full autonomy runtime | [drones_architecture_comparison_paper](https://github.com/asaelbarilan/drones_architecture_comparison_paper) | Planner memory, grounding, streamed VLA actions, monitoring, control/safety and simulator adapters |
| Complete model package | [drone-vla-qwen3vl-4b-step8000](https://huggingface.co/asaelbarilan/drone-vla-qwen3vl-4b-step8000) | Base weights, trained adapter, tokenizer/processor, normalization and inference code; currently private |

The old `drone-vla-training` repository redirects to a repository marked `not-to-use`. Use the training link above.

![Shared model architecture](https://github.com/asaelbarilan/drones_architecture_comparison_paper/blob/main/reports/linkedin_demo_20261017/architecture.png)

## What runs

One frozen Qwen3-VL-4B base is resident on the GPU. The planner, grounding VLM and monitor use the base; the VLA pilot activates the trained D207 stage2 step8000 adapter. GPU calls are serialized. The wall-clock control loop is asynchronous and continues to enforce safety and expiration while generation is in progress. This is not four simultaneous model copies or one interchangeable conversational KV cache.

The planner preserves the original mission, ordered committed steps, completed steps and bounded recent-event memory. Lost target, stalled progress and monitor replan requests invoke constrained recovery planning. Reaching an intermediate visual waypoint requests new grounding, not mission completion. The final stop checks fresh object proximity, visibility and stationarity.

## Reproduce the recorded development experiment

The tested implementation is architecture commit `9c90c5790d5169b0a31dc5b11b234d2bb05bbdb2` (D148). It is local at the time this publication draft was prepared; the remote must be updated after review before an external reader can check it out.

1. Clone the **architecture** repository and install its package/development dependencies.
2. Obtain the complete model package with permission to access the private HF repo. The tested model revision is `75bc5e34a21b8a49be97738c0415c870be673424`; the later evidence-only revision is `b12eb346cf0be6436529d3cf882d01f570024824`. No separate base download is needed.
3. Use a CUDA environment compatible with the tested Windows NF4 setup (Transformers 4.57.3). Install the model package's dependencies; the fast experimental graph backend is hardware/software dependent, not a portable latency guarantee.
4. Copy `configs/experiments/qwen_visual_object.json` to a local config and change **only** `package_path` to the downloaded package directory. Preserve its mission, seed and limits for a comparable run.
5. From the architecture repository in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python scripts/diagnostics/run_qwen_visual_object.py --config path/to/local-config.json --out reports/my_pillar_run
```

Use a new output directory. This launches local inference and a bounded local simulator flight; it is not needed to watch the saved demo. See [D148 report](https://github.com/asaelbarilan/drones_architecture_comparison_paper/blob/main/reports/qwen_event_planner_20261017/REPORT.md) for recorded evidence and exact scope.

## What has and has not been demonstrated

D148 completed one visible red-pillar approach in rendered grid3d: 58.564 seconds, final independent distance 1.332m, visible and stationary, 47 fresh actions and no collisions. Median first action was 205.6ms produced / 253.6ms received on an RTX 4060 Laptop; slowest receipt was 825.1ms. These are not full cognitive-loop times. Four simple numeric cases passed a separate development suite with broad fixed tolerances.

This is not AirSim, real flight, out-of-view search, held-out benchmarking or evidence of general autonomy. No new training was used for these integration improvements. The PPO experiments did not establish reliable improvement. The full package remains private pending review; its recorded licensing questions are not resolved by publishing source code.

## Review assets

[Post draft](https://github.com/asaelbarilan/drones_architecture_comparison_paper/blob/main/reports/linkedin_demo_20261017/POST_DRAFT.md), [video](https://github.com/asaelbarilan/drones_architecture_comparison_paper/blob/main/reports/linkedin_demo_20261017/linkedin_demo.mp4), [diagram](https://github.com/asaelbarilan/drones_architecture_comparison_paper/blob/main/reports/linkedin_demo_20261017/architecture.png), and [review/readiness notes](https://github.com/asaelbarilan/drones_architecture_comparison_paper/blob/main/reports/linkedin_demo_20261017/README.md). No external publication was performed when preparing these assets.
