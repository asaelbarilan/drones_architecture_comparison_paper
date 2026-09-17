# D-129 preflight interrupted by memory exhaustion

The named SPF RGB-D arrival extension is implemented in commit9841cbb. Native
SPF is unchanged.27 focused tests and458 total unit tests passed before flight.
Its surface-point stop radius1m is explicitly different from the unchanged
2m goal-center evaluation. Two distinct VLM localizations support a6s target
track; arrival first holds the vehicle, then requires fresh range and speed
<=0.15m/s beforeSTOP. Extra localization inference is charged separately.

C2 ran31s and approached to a reconstructed3.481991m. It had not reached the
arrival window, held, or stopped. At the next native SPF request, local Ollama
logged std::bad_alloc during image encoding, and returned an empty reply.
The policy correctly failed to parse it; episode_end records runtime_error.
Optional Parquet export then raised ArrowMemoryError for a2944-byte allocation,
so the caller never received the original result and never launched C3.
This is an infrastructure interruption, not evidence for/against arrival.

At diagnosis the machine had about697MiB physical and796MiB virtual memory free,
and only278MiB GPU memory free. A separate local VLA training process used
about13.53GiB working set. That job and shared Ollama11434 were left untouched.
Only our dedicated11435 model was unloaded and owned server44940 stopped;
free physical memory recovered to about5.2GiB. Avoid overlapping these jobs.

## Preserved and reconstructed evidence

- The original runs/c2_spf_arrival_20260917_s1061 directory is unchanged.
- interrupted_c2 copies its manifest, raw events and debug inputs/replies.
  Its result.json is EXPLICITLY reconstructed: saved episode_end gives the
  termination; replay gives final metric/status. It is not a recovered original
  result, and final-state agreement is not an independent verification.
-620 logged poses match replay;31 actual model image inputs match exactly.
  There are30 nonempty replies and one empty recorded reply.
- Four debugger seeks and one playback checked; terminal camera/map/observer
  inspected visually. Target remains visible and ahead at31s, before arrival.
- INFRA_FAILURE.json records original model error lines and resource samples.
- Dashboard: reports/debugger/spf_arrival.html with explicit interruption banner.
- Pending: flight validation of arrival and braking; C3 has not run.

## D-130 evidence preservation fix

After this failed flight, optional EventLog Parquet export now flushes primary
JSONL first and catches MemoryError with an explicit warning. The caller can
receive the already computed episode result even if this optional export fails.
No controls, policy, scoring or termination condition changed. Nine focused
export/debug-capture tests pass, including injected ArrowMemoryError and retained
termination records. The failed original result is not retroactively invented.

## Next

The user goal remains active. Do not interrupt the independent training job.
Before loading the dedicated VLM, require useful host and GPU headroom (suggested
pre-load gates: >=10GiB available virtual memory, >=8GiB physical and>=5.5GiB GPU).
Freeze any replacement flight with a new ID and an explicit infrastructure-retry
rationale; keep this attempt. Never reset the original STATE to frozen or overwrite
its run. Run the arrival preflight, audit exact camera/controls and stopping speed,
then the matched verifier condition if resources remain sufficient. No fresh
inference is currently queued, and no additional permission is required.
