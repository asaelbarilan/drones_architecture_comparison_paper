# D-124: unchanged C5 validation on two more development seeds

**No new completion in four flights.** Target commitment remains a useful mechanism
on the earlier successful seed1061, but is not a general navigation solution.
The new cases distinguish false target identity and unsuccessful search from the
correct-target occlusion case. Keep this variant frozen; do not tune these results
away or replace the earlier evidence.

| Seed | Commitment | Outcome | Time (s) | Closest (m) | Final (m) |
|---|---|---|---:|---:|---:|
|1060|Off|Diagnostic stop, censored|199.0|24.864|46.029|
|1060|On,20s|Full timeout|240.0|24.766|93.142|
|1062|Off|Diagnostic stop, censored|171.0|20.091|61.248|
|1062|On,20s|Diagnostic stop, censored|169.0|20.091|58.519|

All four have zero collisions/out-of-bounds. All had240s maximum, same fixed local
Qwen3-VL4B digest and GPU placement, prompts and flight stack as D-123. The three
censored runs meet the predeclared45s stationary/no-turn/repeated-goal rule; their
remaining time was not observed. Do not call them full240s failures or estimate
uncensored success probabilities from this small batch. The retained successful
seed1061 completes at71.2s; one of three tested enabled cases has completed so far.

## Seed1060: target identity before target persistence

At policy request4s the actual input shows a GREEN pillar; the response says
"green vertical structure" but kind=target for a RED-tower mission. At53s a green
rectangle is again called target. Exact images and selected pixels were inspected.
Off makes2 target proposals; on makes7. Both begin with the same incorrect identity.
On activates leases at7s and56s, sourcing4.95s and53.95s observations. The original
source/timestamp/20s nonrenewing deadline audit passes;92 older-than4s commands are
explicitly leased. Retaining a mistaken target can prolong the mistake.

Inputs/replies match before7s; first control difference and first lease both7s.
This supports the observed arbitration mechanism, not a claim that commitment
alone explains every later trajectory difference. Later identical sky-image
requests sometimes receive different wording even at temperature0.

The independent monitor never acquires the red target and issues only CONTINUE.
Before confirmed acquisition, LOST is normalized to CONTINUE by design. Thus this
monitor does not correct the fast policy's green-target identity or initiate a
new search recovery here. This is a specific coordination/search boundary, not
proof that VLM navigation generally fails. Geometry acceptance does not certify
semantic identity. No new color detector or prompt patch was introduced.

## Seed1062: no target proposal, no commitment activation

Both variants produce zero target proposals and zero leases. Inspected early
views show gray buildings; later views show empty sky/ground. Do not infer from
these sampled images that the target was never visible anywhere in the flight.
What the logs establish is that the policy never proposed it and the monitor
never confirmed acquisition. Both approach20.09m at34.75s then fly away.

At policy request6s, identical inputs already produce different v coordinates
(450 versus500). Controls first diverge45s, with no lease ever active. The later
trajectory difference cannot be credited to the commitment switch. Configuration
matching and temperature0 do not guarantee identical generated outputs.

## Shared terminal failure and next isolated diagnosis

All four eventually repeat rejected goals beyond the flight boundary while the
vehicle itself remains inside it. First rejection times/counts:1060off141s/59,
1060on172s/67,1062off120s/52,1062on117s/53. Exact last prompts and feedback are in
per-run MECHANISM.json; empty-camera late views were inspected in the dashboard.
Boundary deadlock is a downstream symptom of unsuccessful search here. Separately
study how to recover from repeated rejection, but do not claim that fixing only
that terminal symptom solves original target identity/search.

Next C5 work should use saved frames to isolate semantic target confirmation and
pre-acquisition search/rejection recovery. Freeze target commitment as a named
extension, not native paper fidelity. No further C5 flight or tuning was launched.

## Validation and reproducibility

15,583 control positions replay exactly; all1,173 actual input images match their
source frames, including cancellation captures.40 browser seeks/four playbacks
pass; combined four-run selector also works. Saved camera/observer/map views and
wrong-green-target examples were visually inspected; see VISUAL_REVIEW.json.
Five harness tests passed.1,166 completed local calls plus7 cancellations, zero
cloud calls or model downloads. Tiny speed exceedances are <=2.22e-16m/s roundoff.

SOURCE_INTEGRITY.json verifies src tree and resolved C5 configs unchanged during
flights. Manifest commits differ because comparison preparation/report files were
committed while flights ran; runtime source snapshots are retained. The later
D-127 diagnostic-message correction does not change navigation or these outcomes.

Dedicated11435 model unloaded/server stopped; shared11434 and Valley untouched.
Debugger8766 remains available. STATE files mark audited completion.
Dashboard: http://127.0.0.1:8766/commitment_validation.html
The C2/C3 follow-on preflight is documented separately in
reports/c2_c3_preflight_20260916/REPORT.md.
