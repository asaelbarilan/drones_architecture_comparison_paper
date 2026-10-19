# LinkedIn post (VLA focus): review draft, not published

I work on autonomous drone architectures, and I wanted to research them without expensive hardware. I couldn't find open-weight drone VLA (Vision-Language-Action) models that fit on an 8 GB GPU. So I trained one.

It's built on Qwen3-VL-4B with a LoRA adapter. (I also tried SmolVLM, but the small models often couldn't even produce a valid action, so I dropped them.)

Why it's interesting:
• It runs on an 8 GB laptop GPU (RTX 4060): first action in 254 ms, a full chunk of 8 flight commands in ~0.75 s, so it can fly continuously.
• The same model runs a whole drone architecture: five roles (planner, recovery planner, visual grounding, pilot, monitor), asynchronous, all sharing one 4B base model in ~5 GB of VRAM. I haven't found another setup that does this on such a small compute budget.
• On UAV-Flow it reached 82% success on 100 held-out validation tasks. For reference, the published test-set results are 65.6% for OpenVLA-UAV and 79.1% for the recent 7B WorldVLN. Mine is on validation, not yet on the official test set, so it's not a like-for-like comparison yet.

What made a 4B model this accurate (none of it was trivial):
• A "progress line": the model also predicts how much of the flight is left, in the drone's own frame. It learns where it is in the task, not just the next move.
• Goal memory + a deadband: the first goal estimate is kept, and the drone stops trying to fix tiny errors (1 m / 5°), so it no longer keeps drifting near the end.
• Real + simulated flights mixed, with mirrored and photo-augmented images, and a small share of "find the box" grounding examples so it keeps using the camera.
• One round of DAgger (correcting its own mistakes from its own flights): the hardest classes went from 61.6% to 74.0%.

More about the training in the blog post and repos:
[blog link]
https://github.com/asaelbarilan/drone_small_vla_training
https://github.com/asaelbarilan/drones_architecture_comparison_paper

#Robotics #VisionLanguageAction #EmbodiedAI #Drones #EdgeAI
