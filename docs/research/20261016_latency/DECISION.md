# Start with time to a usable action

The review retained 26 meaningfully inspected sources from 30 candidates,
including 18 primary papers. Machine validation checks coverage, not truth or
transfer. Full deployment compatibility remains unproven where explicitly marked.

The local pilot computes 32 causal tokens (eight four-dimensional actions), while
the current controller consumes only the first action. Measure and expose the
first quartet immediately. A one-action request may stop after four tokens;
the input prompt/codec must remain the original eight-action format. This is an
execution optimization, with exact prefix equivalence checked locally (D02).

Keep control in the parent process and one GPU owner in a spawned worker. Queue
bounded requests, serialize adapter switching, carry observation identity and
monotonic capture time, cancel revoked work, and reject stale output at consumption.
This follows asynchronous execution evidence (R03,R07,R08), but does not implement
RTC flow inpainting or assert that every remaining chunk action is safe to execute.

## Options and order

| Order | Option | Evidence | Local acceptance / reason to defer |
|---|---|---|---|
| Now | Stream complete quartets; request only consumed actions | D02, causal codec | Exact action tokens; actual first-action timing |
| Now | Separate control and inference processes | R03,R07,R08 | Control tick remains responsive; stale/revoked output rejected |
| Existing | Exact KV/image reuse | L05,L09,D133 local negative evidence | Changing images miss; no approximate cross-frame reuse |
| Next measurement | Restrict pilot output projection to action vocabulary | Local model inspection | Profile LM head first; preserve adapter/modules-to-save semantics and validate logits/tokens |
| Next measurement | Fixed-shape decode, compile/CUDA graphs, fused kernels | D01,L03,L08 | Test installed NF4/PEFT graph compatibility; measure warm and cold latency |
| Separate A/B | AWQ/GPTQ + optimized serving kernels | L03,L06,L07,D05 | Requantization is approximate; full vision/language adapter coverage required |
| Later A/B | Smaller visual context/crops or token pruning | L01,L02,L09,D03 | Measure small-target/heading/altitude task quality, not only token agreement |
| Research | Prior-action proposal verified by current causal model | D01,S02 | No extra draft weights; measure acceptance and verify exact tokens under NF4 batch-shape changes |
| Excluded | New flow head, learned corrector, parallel-action fine-tuning | R09,L10,D08 | Requires another trained policy/head |

No kernel change, pruning or lower-resolution image is selected by this document.
NF4 already solves memory fit; it does not prove optimal speed. FlashAttention's
Windows support is less established, and server throughput is not single-request
latency. One base remains resident; planner/monitor use disabled adapters and pilot
uses D207. Their KV histories stay separate; vision features cannot cross differing
vision weights. Detailed official resources and license gaps are in the ledger.

## Remaining implementation phases

1. Measured streaming/worker primitive, isolated from virtual-time replay.
2. Persistent VLM-approved goal, priority/event scheduling and bounded action
   execution connected to the existing shield/controller; no VLM call per action.
3. Bounded local simulator test of fresh observations, arrival, revocation and
   hover during cognition. The current Project AirSim adapter is a placeholder.
4. Search/inspect/remember tasks and optional cheap tracking/grounding. Evaluate
   task correctness independently of latency (R01,L11,D07).

Research ideas if latency remains high: profile head versus attention versus NF4
linear kernels; verify cached previous action proposals instead of training a draft;
test fixed tensor shapes with stable MRoPE; measure CPU thread contention and image
serialization separately. Reject an idea if it changes causal tokens, makes control
miss deadlines, increases stale-observation use, or loses semantic task accuracy.
