# D-132 local shared-Qwen integration

The one-base design works on the local RTX4060Laptop8GB. It is a development
integration, not evidence that the complete architecture navigates reliably.

Final evidence: [result](final/result.json), [all role calls](final/calls.jsonl),
[camera input](final/input.png), [first simulator view](final/step_0.png).
Model: complete local D207 step8000 package, NF4 base with unmerged LoRA.
No AWS, training, weight updates, or deletion.

## Checks and measurements

- 44 focused CPU/regression checks passed, including direction/action frame
  conversion, invalid outputs, early-stop rejection, arrival-before-goal-refresh,
  adapter restoration after language-call failure and configuration loading.
- One base load for all12 model calls. Planner/direction/monitor disable LoRA;
  pilot enables it. Base planner text and full next-token logits are exactly equal
  before and after pilot switching. This tests one fixed context, not all inputs.
- Peak PyTorch allocated GPU memory:4,470,585,344bytes (4.16GiB), measured during
  the role/switch probe. This is not total driver-reserved memory.
- Five-call contract/switch phase:27.53s including model load. Total recorded
  inference time including the short simulator sequence:47.66s.
- GPU returned to12MiB used after the preceding probe; final cleanup is verified
  separately below. No model server is left running by this script.

## Actual behavior

On the initial image the base VLM correctly said the red tower was not visible;
the monitor requested replan. A separately labelled numeric pilot fixture
returned eight approximately0.20m forward steps. It was not executed against the
monitor's replan: this fixture isolates the action decoder and adapter switching.

Then the actual integrated policy received “Move forward2meters” with fresh images.
Planner, direction, monitor and VLA produced two actions. Simulator poses:

| Point | East(m) | North(m) | Altitude(m) |
|---|---:|---:|---:|
| Start | 0 | 0 | 3 |
| After step1 | .054806 | .048560 | 2.999710 |
| After step2 | .172143 | .152704 | 2.999216 |

The start heading is not world+x; ENU east/north movement follows that heading.
Each action ran0.5simulatedseconds in20Hz physics substeps. Total displacement
is about0.23m. This is a two-step wiring test, not completion of the2m task.
The simulated world was explicitly paused during inference; no shield/router
or real-time flight validation was performed by this standalone probe.

## Issues exposed, not hidden

The direction role described a target box for a numeric movement instruction
despite no uniquely specified visual object. Its selected point also implies
a slight lateral/downward local goal. That semantic interpretation needs review.
Strict JSON parsing does not establish correct grounding.

Warm loops take roughly10seconds. The full runtime correctly charges measured
latency; the inherited1.5second staleness bound would reject such decisions.
We did not weaken it or report paused simulation as real-time performance.
Next integration work is visible-target point validation plus explicit hover and
fresh-observation scheduling, before mission trials. AirSim has not been tested.

## Audit history

The first restricted async processes were cancelled before model evidence.
An initial elevated probe did progress to two calls before being cancelled during
startup diagnosis; root calls.jsonl preserves those partial records. The verified/
probe established the shared-base result; final/ additionally corrects pilot state
to start-relative measured pose rather than zero on every observation. Use final/
as the authoritative result. No scene/outcome-selected retries were performed.

Final cleanup: nvidia-smi independently reports12MiB GPU usage after process exit.
