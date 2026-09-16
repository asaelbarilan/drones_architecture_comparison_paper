# D-126: matched C2/C3 visible-target preflight

**Both physically reach0.836m but fail to declare STOP, then leave permitted bounds.**
Neither configuration is ready for a clutter or architecture-ranking claim.
These are normalized SPF C2 and SPF+verifier C3; only the gate/identity differ.
The retained localQwen3-VL4B backend, calibrated camera, shared execution and240s
maximum are identical. This follows the four unchanged C5 validation flights.

| Variant | Closest/time | Terminal time | Terminal cause | Final distance |
|---|---|---|---|---|
|C2|0.83584m at27.15s|82.6s|Horizontal radius45.0249m exceeds45m|33.117m|
|C3|0.83584m at27.15s|82.3s|Altitude0.499768m below0.5m|32.558m|

Both have zero collisions. Both enter the2m goal region at23.1s and continue past
it. The visible red pillar grows to fill most of the actual camera image at25s.
The VLM still emits distance=3; after the target leaves view it emits5. Neither
flight ever emits1 or2, the values needed by the existing repeated-near-label STOP
rule. There are zero STOP proposals. This isolates the immediate arrival/stop
failure from parser, transport or lack of physical reachability. It does not yet
establish whether a changed prompt/output representation or a separate stopping
contract is the appropriate repair. Do not silently copy C5's monitor into C3.

The schema's distance means intended travel, with visual-size categories in the
prompt; it is not calibrated physical range. The archived input/output at24–26s
is the next offline contract case. RGB input and source alignment are verified.

C3 rejects four outside-fence proposals at79–82s; C2 has no proposal verifier.
However, controls already differ65s, before those rejections, so final distances
are not an isolated quantitative gate-benefit estimate. Model outputs vary despite
matched settings. The C3 gate prevents those proposed boundary goals, but the
vehicle still crosses the altitude floor while slowing. Diagnose that separately
with the saved final state; no safety margin or control change was made here.

The original result calls both cases "left the geofence". C3's x44.462m is inside
the horizontal fence: its altitude is the violated constraint. D-127 corrects
future diagnostic text after these flights; original event/result evidence remains
unchanged.31 bounds/scenario tests pass, including the exact C3 terminal altitude.

## Evidence and limits

3,300 recorded control positions replay exactly;166 actual model-input images
match, including two cancellation captures.164 completed local calls,2 cancelled,
no cloud.14 browser seeks/two playbacks pass, and camera approach/overshoot views
were visually inspected.10 preparation/SPF contract tests passed before flights.
No extra flight, tuning or retries followed. These results are not task successes.

The source and model identity snapshots, outputs and final state are retained in
per-variant AUDIT.json, manifest/result files, images/calls and compressed events.
Prepared normalized profiles retain their development status. Old C3 OnFly
no-stop diagnostic remains preserved and was NOT used for these two flights.

Next: reproduce the24–26s close-up STOP failure offline using saved requests;
separately reconstruct the final C3 altitude/control boundary. Re-run a flight
only after one intended contract change is independently checked. Broader task
comparison waits for this interface to work, rather than counting fly-through as
mission success or attributing every timeout to planning ability.

Dashboard: http://127.0.0.1:8766/c2_c3_preflight.html
Dedicated model/server stopped; shared11434/Valley untouched; debugger8766 retained.
