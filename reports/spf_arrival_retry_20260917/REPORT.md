# D-131 replacement flights: prepared, not started

The D-129 arrival extension and two replacement C2/C3 configurations remain
unchanged. Fresh seed1061 run IDs and240s limits are frozen in FREEZE.json.
No replacement run directory or flight was created. No image inference occurred.

The first VLA training process PID16380 exited. The before-load check passed
(16.30GiB physical/25.43GiB commit/5.99GiB GPU at the archived sample), and a second
check immediately before starting the dedicated server also passed
(10.37/19.32/6.76GiB). While the model loaded, a new expanded-condition VLA training
process PID24992 grew to about15.86GiB working set. The after-load check found
1.685GiB physical,1.572GiB commit and0.598GiB GPU available. It refused admission
before either flight or image request. RESOURCE_START.json retains that sample.
Dedicated server43524 was unloaded and stopped; training/shared11434 untouched.

This confirms that a pre-load check alone cannot reserve capacity against another
job. Both admission stages are needed. Eleven offline gate tests pass, covering
unknown/nonfinite values, the recorded allocation-failure levels and distinct
before/after thresholds. Scripts are lint-clean. Navigation code did not change.

STATE remains frozen with an empty run list: it is safe to attempt this exact
batch after headroom remains available. Do not recreate the freeze, change model
or overwrite the interrupted D-129 attempt. Before loading, run
scripts/local_inference_resources.py and require exit0; after loading, the runner
checks again. Run scripts/run_spf_arrival.py --replacement only when admitted.
No process is waiting in the background and no further calls are queued.
Goal remains active; arrival/braking validation is incomplete.

## Goal status update

Third consecutive goal turn confirmed the same external memory blocker with live
training PID24992. See BLOCKED_AUDIT.json for current readings and remaining scope.
Goal is blocked, not complete; resume the same frozen pair after memory release.
