# LinkedIn post — review draft, not published

I've been building a small drone VLA — and connecting it to a complete local control system.

One Qwen3-VL-4B base model serves four roles: a language planner, visual grounding, a VLA pilot with a trained adapter, and a visual monitor. The control loop runs asynchronously; the model calls share one GPU and run one at a time.

The video replays a recorded simulation task: find the red pillar, approach it, and stop nearby while keeping it visible. The system stopped 1.33m away, within the fixed 1.5m requirement, with no collisions. This is a development demonstration, not a general-autonomy benchmark.

A useful lesson: reaching a short waypoint is NOT the same as completing the mission. The planner now keeps the original goal and ordered steps in memory. Waypoint arrival triggers fresh visual guidance; task completion requires fresh proximity evidence and a visual check.

On my RTX 4060 Laptop GPU, the pilot's median time to its first usable action was 206ms produced / 254ms received by the runtime. That's action latency, not the latency of the whole planning system, and not a guaranteed deadline.

Next: unseen scenes, distractors and recovery tests, plus fair comparisons with simpler controllers.

Training code: https://github.com/asaelbarilan/drone_small_vla_training
Architecture: https://github.com/asaelbarilan/drones_architecture_comparison_paper
Model: https://huggingface.co/asaelbarilan/drone-vla-qwen3vl-4b-step8000 — currently private; not a public download yet.

#Robotics #VisionLanguageAction #EmbodiedAI #Drones #OpenSource

---

## Reviewer notes (not part of the post)

- Attach `linkedin_demo.mp4`; use `poster.png` as the cover. `architecture.png` is the companion diagram.
- This is a silent, captioned replay of D148, using actual saved model-input camera frames and recorded telemetry at 1x. It is not a continuous camera recording; frames are held between saved model requests, as labelled throughout.
- Both GitHub repositories are public. The latest architecture implementation and this demo are LOCAL ONLY, pending review and a normal push. The old `drone-vla-training` URL redirects to `drone-vla-training-not-to-use`; do not use it.
- HF is independently verified private at revision `b12eb346cf0be6436529d3cf882d01f570024824`. Keep the explicit private label unless visibility is deliberately changed later. No visibility change has been made.
- The existing HF card still records pending UAV-Flow/derivative licensing review. Do not call the weights an open-source release or change them to public before resolving that recorded issue. The code links and demo can be presented while the model remains private.
- No PPO improvement claim. This uses the retained supervised D207 step8000 adapter.
- No Jetson, real-drone, AirSim, obstacle-avoidance or general recovery claim. Planner recovery was tested with injected events, not exercised naturally in this particular flight.
- This post intentionally omits the older 82/100 training result: its evaluation protocol differs from this architecture demo.
