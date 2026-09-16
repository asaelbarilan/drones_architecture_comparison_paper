# D-125: C3 comparison preparation (no new model calls)

The latest ASP-UAV_Final_Research_Design.pdf, page3, defines C3 as C2 plus
semantic/geometric verification. Its causal control is C2. C5 adds monitoring
and memory; comparing C3 with the successful target-commitment C5 changes several
mechanisms and must not be described as an isolated verifier experiment.

## Existing profile problem

c3_onfly_qwen4_shared is an OnFly decision-only diagnostic, not the complete
SPF-plus-verifier condition. Its policy emits only waypoints with stop_at_target=false;
its monitor is absent. The task requires an explicit terminal stop. Toggling the
inherited self_terminate parameter does not add a stop branch to OnFly.decide.
STOP_CONTRACT.json records six offline stub outputs at0.8m depth, all waypoints,
with self_terminate false and true. This is a routing-contract probe, NOT evidence
about actual target perception or navigation. Source inspection confirms both
return paths construct waypoints and never call BasePolicy's stop helper.
The historical Qwen profiles also reference an old checkpoint digest; no reinstall
or old-model flight is appropriate. Historical files are preserved.

## Prepared comparable configurations

- c2_spf_qwen4_current_dev: existing SPF point-plus-distance policy, own existing
  repeated-near-label STOP output, current retained Qwen3-VL4B checkpoint.
- c3_spf_qwen4_current_dev: identical to that C2 except a semantic_geometric gate,
  with max proposal distance10m, minimum clearance1.8m, repairfalse, horizon25m.
  Symbolic semantic support is disabled because normal RGB-D observations do not
  contain labeled detections. The model still chooses all semantic points.

Both reuse D-123's exact perception, SUPER, controller, inference settings and
staleness parameters. No monitor, recovery or semantic memory. C2/C3 differ only
in the verifier and identity fields, checked by test. C5 remains unchanged.
These are explicit normalized development profiles, not accepted native SPF
reproductions. Model distance mapping, prompt and stopping mechanism differ from
C5; therefore cross-family comparisons will be whole-system comparisons.

## Verification and next executable sequence

10 focused tests pass: two comparison-control tests and eight existing SPF policy
contracts, including strict output schema, pixel lift, explicit stop after two near
labels, and forbidden truth/depth input checks for the SPF policy. No inference.
Prepared YAMLs and resolved snapshots are retained for review/reproduction.

Next run the SAME visible-target development fixture with C2 and C3 before clutter.
Keep 240s outer budget and task scoring identical within the pair. Preserve
premature-stop outcomes: SPF's near-travel label is not certified physical arrival,
and currently provides weaker target identity/range evidence than C5's monitor.
Inspect actual inputs and output-channel parsing before attributing errors to the
architecture. Do not add a monitor to C3 just to obtain a stop. Once that contract
works with the retained model, run matched C2/C3 clutter and then other task types.
The four-flight D-124 validation budget is not extended by this preparation;
no C2/C3 real-model flight has been launched or claimed successful.
