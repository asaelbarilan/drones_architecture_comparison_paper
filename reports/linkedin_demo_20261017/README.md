# LinkedIn demo — local review package (D149)

**Nothing has been published, pushed, uploaded, or made public by this preparation.**

Open [review.html](review.html) for video, diagram, post and release notes together.

## Deliverables

| Asset | Contents |
|---|---|
| [linkedin_demo.mp4](linkedin_demo.mp4) | About 85 seconds; silent burned-in captions, H.264/yuv420p, 1600x900, 20fps, fast-start |
| [poster.png](poster.png) | Video cover |
| [architecture.png](architecture.png) / [architecture.svg](architecture.svg) | Raster and editable vector diagram |
| [POST_DRAFT.md](POST_DRAFT.md) | Ready-to-review post with GitHub and private HF links; reviewer notes separated |
| [training_repo_preview/README.md](training_repo_preview/README.md) | Training repository's full README with proposed architecture entry point |
| [training_repo_preview/docs/FULL_DRONE_SYSTEM.md](training_repo_preview/docs/FULL_DRONE_SYSTEM.md) | Full-system guide intended for the training repo |
| [training_repo_crosslinks.patch](training_repo_crosslinks.patch) | Exact two-file patch; `git apply --check` passes in the training repo; not applied |
| [link_verification.json](link_verification.json) | Read-only live visibility/link checks |
| [media_manifest.json](media_manifest.json) | Timing, source identity and video hash |

## What the video actually shows

The existing D148 real-model development flight, not a new run. Six-second introduction; original ~58.6-second flight at 1x; two-second final-state hold; nine-second architecture; nine-second outcome. Its camera is the actual saved model-input images, held until the next saved input, explicitly labelled. There is no fabricated in-between camera imagery. The trajectory and distance are offline visualization of recorded ticks and evaluator truth, not hidden inputs passed to the policy. GPU role indicators use recorded submission/completion timestamps. Last accepted boxes and executed action deltas are displayed from logs.

The final monitor result occurs about 1.4ms after the timestamp assigned at the start of the last controller tick. Replay includes the recorded final event tail so it shows the actual stop verdict rather than incorrectly leaving the monitor marked running. The final-state hold is presentation time, not extra flight time.

No audio, music, synthetic narration or new model inference. No AWS, training, simulator launches or hardware changes. D148 weights/configuration/evidence remain unchanged. Rendering uses CPU FFmpeg/Pillow.

## Claims supported

- One shared Qwen3-VL-4B base, D207 step8000 adapter activated for the pilot, serialized GPU calls and asynchronous control.
- One recorded visible-pillar approach passes unchanged 60s/1.5m conditions: 1.332m, visible, stationary, 47 fresh executed actions and no collisions.
- Twenty pilot calls: median first action 205.6ms produced / 253.6ms received, maximum receipt 825.1ms. Not a guaranteed deadline or full cognitive-loop latency.
- Four simple numeric development cases passed a separate D145 suite with broad fixed tolerances. No claim of independent held-out success rate.
- Event recovery exists and passed injected-memory probes; it did not occur naturally in the showcased flight. No claim of general recovery, AirSim or real-drone readiness.
- PPO did not establish reliable improvement; this uses the retained supervised adapter.

Evidence: [D148 report](../qwen_event_planner_20261017/REPORT.md), [raw event archive](../qwen_event_planner_20261017/real_v1/raw_events.zip), [component audit](../qwen_event_planner_20261017/real_v1/component_audit.json), [D145 four-case report](../qwen_completion_fix_20261017/REPORT.md). Tested implementation: `9c90c5790d5169b0a31dc5b11b234d2bb05bbdb2`.

## Repository arrangement

Keep training and architecture source separate, consistent with the training repo's AGENTS.md. Add an obvious training README entry point plus a full-system guide containing the architecture diagram and canonical code link. The training repo will then explain and link the complete architecture without maintaining a second drifting copy of the runtime.

The architecture README has been updated locally to point to [the new full-system guide](../../docs/FULL_DRONE_SYSTEM.md). The training-side change is a concrete patch and full-file preview, not a remote modification.

Verified on 2026-10-17:

- Training repo: public, main `3bb5c20e0c88c17d411c0701237c91b1c4a48647`.
- Architecture repo: public, main `d5f01c5730fd9176cf462c8bcd8dfb397cb98a7b`. D148 is 20 local commits ahead; that remote revision is an ancestor of local HEAD. The demo/runtime additions are not yet available at the public link. A later push must review the entire unpublished range, not assume this is a two-file upload.
- Old `drone-vla-training` link redirects to `drone-vla-training-not-to-use`; excluded from draft.
- HF complete model exists at `asaelbarilan/drone-vla-qwen3vl-4b-step8000`, revision `b12eb346cf0be6436529d3cf882d01f570024824`, and remains **private**. Anonymous request returns401. No claim that others can download it.
- Existing HF model card retains unresolved UAV-Flow/derivative licensing review and stale pre-smoke wording. That card should be reviewed/corrected before a public model release; code publication alone does not resolve the license question.

## After user review only

1. Approve or edit the media and post.
2. Apply the prepared training cross-link patch, document it in that repo, and review the unpublished architecture range before normal pushes. Never force-push or duplicate architecture source into the training repo.
3. Keep HF private with the draft's explicit label, or separately resolve the recorded license/card issues and authorize public visibility. No such change has been made.
4. Recheck the public links, then publish only the approved post/media. No publishing authorization is inferred from this review request.

## Rebuild

From the architecture repo, with Pillow, NumPy-free trace reader and FFmpeg available:

```powershell
python scripts/diagnostics/build_linkedin_demo.py
```

This reads the checked-in D148 event ZIP and PNGs. It does not need model weights, a GPU, HF access or any simulator.
