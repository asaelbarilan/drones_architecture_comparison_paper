# D-128: saved-frame SPF arrival diagnosis

Completed 2026-09-17. Nine local Qwen3-VL 4B calls, no retries, no new flight,
no deployed policy or configuration change. Frozen baseline commit 8290a7d.

## Findings

1. Exact original prompt/schema repeats on request 24 s and 25 s both return
   `{u:500,v:500,distance:3}`, matching the original flight. Source goal-center
   distances are 1.614 m and 1.273 m; red occupies 60.7% and 89.3% of image width.
   The prompt asks for label 1 above 35%, and native STOP requires consecutive
   labels <=2. This observed label failure prevents STOP despite arrival.
2. Localization-only prompts on the same PNGs accurately locate the pillar:
   box IoU 0.987 and 0.990. A narrower task can extract the image location;
   this does not demonstrate simultaneous navigation and reliable termination.
3. The prompt's near-label visual rule is itself unsuitable as a metric arrival
   certificate: at source 19.95 s, red width is 26.8% but goal-center range is
   3.413 m, outside the 2 m success radius. Fixing label compliance alone is
   insufficient. No width-only STOP change was deployed.
4. At source 25.95 s, red fills the image. Localization replies visible=false,
   describing an entirely red image with no visible pillar. This is loss of
   semantic recognition under an extreme crop, not an absent-red image.
   Across the seven selected cases: 6/7 pass (4/5 positives, 2/2 negatives).
   This single diagnostic does not establish robust target identity.

## Corrected interpretation

D-126 associated the later label 5 sequence with the target leaving the camera.
The saved request at 26 s already outputs label 5 on the red-filled 25.95 s
source. That earliest label change cannot establish target disappearance.
The actual absent control is source 39.95 s. Old records remain unchanged;
this correction supersedes that interpretation, not the recorded flight results.
The initial D-128 preparation also called source26 absent; it was corrected
before inference and retained in PREPARATION_REVISED_BEFORE_CALLS.json.

## Offline geometry check

Replaying the original controls verifies 801 poses and all six selected C2
RGB images exactly. At the VLM bounding-box centers, reconstructed depth gives
ranges 12.227, 3.564, 1.477 and 0.992 m for far, width-threshold, close24 and
close25 respectively. These separate the sampled far/near cases without
using a truth location to select a pixel. Close24/25 world points differ by
0.259 m. No target point is returned for full_close26 or absent.

These are distances to selected visible surface points, not necessarily to
the task's goal center. Clipped boxes also shift the sampled surface point.
Depth feasibility therefore does not establish equivalent task scoring,
correct stopping time, braking, persistence, or closed-loop success.
This check uses reconstructed depth offline; deployed native SPF remains RGB-only.

## Reproducibility and visual audit

- FREEZE.json records prompts, source calls, annotations, model digest and options.
- calls/*.json preserves actual PNG base64 request bodies, both reply channels,
  parsed answers, timing and per-call residency. JSON was read explicitly from
  the configured thinking channel; no silent channel fallback.
- Model: qwen3-vl:4b, digest
  1343d82ebee38e26a4dd6b0180b915eb91550184e67c505dea97509571c8f683.
  Temperature0, seed0, context8192, output192, think=false. GPU residency checked.
- All nine request PNGs match frozen originals byte for byte. Numerical truth,
  color-mask annotations and desired answers were not provided to the model.
  Annotations are evaluation-only; no color detector entered the policy.
- Localization positives use center-in-target and IoU>=0.5; negatives require
  visible=false. Exact outputs and scores are in SUMMARY.json.
- DEPTH_CHECK.json is reproducible with scripts/replay_spf_stop_geometry.py.
- Dashboard: reports/debugger/spf_stop_contract.html, reproduced with
  scripts/build_spf_stop_report.py. Seven actual source images and overlays
  inspected visually. Browser checked all seven image loads, four boxes,
  both toggle states and no page errors. Screenshots retained.
- Dedicated Ollama11435 unloaded/stopped; shared11434/Valley untouched.
  No downloads, cloud calls, key reads, or pending inference.

## Next bounded change

Separate target localization from the metric arrival contract in an explicitly
named extension; keep native SPF as the failed reference. Before a fresh flight,
resolve surface-versus-center semantics and test source age, current pose,
invalid/background depth, target identity continuity and stopping behavior.
Do not infer a target from red filling the view alone, or silently inject truth.
An RGB-D termination interface adds capability beyond native RGB-only SPF and
must be reported as such. This is a proposed next experiment, not a validated fix.
The independent C3 altitude-boundary issue remains open.
