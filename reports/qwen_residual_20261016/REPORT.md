# D-140: restore the earlier half-second first action

The local worker now requests Windows HighQoS for execution speed, in addition
to D139 performance-core placement. This restores the earlier typical warm
latency without changing the model, inputs, sampling, action count or expiry.

## Same measurement as the earlier result

These are the actual spawned worker's first complete action, measured at IPC
consumption from request submission, on the same saved D135 forward/turn inputs.
Planner, direction and monitor calls run on the same loaded base between pilot
requests. These are saved-input timings, not camera-to-action flight timings.

| Worker run | Warm count | Warm median | Warm range | Cold first action |
|---|---:|---:|---:|---:|
| Historical D136 | 6 | approximately 0.55s | 0.531-0.572s | 1.081s |
| D139 placement only | 6 | approximately 0.83s | 0.750-0.982s | 1.423s |
| D140 placement + latency QoS | 6 | 0.518s | 0.510-0.562s | 1.025s |
| D140 fresh worker, longer repeat | 20 | 0.535s | 0.515-0.638s | 1.087s |

Longer repeat empirical p95 (nearest-rank) is 0.614s; twenty warm samples are not
a production tail guarantee. The unchanged startup gate afterward passes three
warm samples at 0.559/0.558/0.559s, inside its existing 1.45s threshold. This gate
was run after replay in the same worker, not presented as a fresh cold-start test.
Cold work remains about one second and is excluded from warm claims.

All compared action tokens/decoded actions match historical D136 over the common
delivered prefix. All planner/direction/monitor result payloads match too. Full
eight-action chunks still cancel at the original 1.5s expiry; timely first action
does not imply whole-chunk delivery. Ready evidence confirms one model load.

## Why core placement alone was insufficient

D139 read ControlMask=0 and StateMask=0 and correctly called this no *explicit*
power throttling. That is not an explicit request for high-performance execution:
Windows can choose QoS heuristically when the process leaves it system-managed.
Microsoft documents HighQoS as explicitly controlling EXECUTION_SPEED and turning
that throttling mechanism off. QoS can affect core selection and processor power
management separately from scheduling priority:

- [SetProcessInformation](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setprocessinformation)
- [Windows Quality of Service](https://learn.microsoft.com/en-us/windows/win32/procthread/quality-of-service)

Within one loaded model, performance-core affinity and original16 threads held
constant, five alternating blocks of10 calls produced:

| Execution QoS | Median first action |
|---|---:|
| Inherited/system managed | 0.851s |
| Explicit latency/HighQoS | 0.505s |
| Inherited again | 0.826s |
| Explicit latency again | 0.567s |
| Inherited restored | 0.756s |

All50 action outputs matched; original affinity and QoS masks restored. This
supports a causal effect of the process execution-speed hint in this session.
It does not identify which automatic QoS class Windows used at every instant or
prove every historical slowdown had this cause. P-core subsetting and reducing
thread count were also tested (48 calls); they did not reliably restore0.55s.
No such subsetting/thread-count change was promoted.

## Change and validation

`cpu_qos.py` scopes the hint to the spawned inference process, before model load.
It preserves unrelated timer-policy bits, verifies the applied state, and restores
the original state on exit/error. No elevated scheduler priority, global power
plan, timer setting, driver change or other application is modified. HighQoS
requests performance rather than energy-saving execution while the worker runs.
Generic worker default remains `inherit`; the existing local experiment now sets:

```json
{"cpu_placement": "performance", "cpu_qos": "latency"}
```

This uses exactly the existing backend SHA256
`a4ada32b291de6b50b3302cab733efdd56333f5fe2495fd41fbe78ea8975552e`, matching D134/D136.
No model precision/weights, prompts, image resolution, caching, sampler, action
count or freshness change. Frozen/version checks pass in the placement diagnostic.
80 focused tests pass for QoS restore/preservation, affinity, worker IPC, action
expiry, caches and async runtime. Ruff and repository code limits pass. All GPU
processes exited; independent nvidia-smi reports12MiB and0% utilization.

Evidence: placement/, qos/, worker/, worker_repeat/, comparison.json and
verification_local.json. No flights, AWS, training or dependency installation.

## Reproduce locally without executing actions

From the repository root with PYTHONPATH=src and the GPU environment Python:

```text
scripts/diagnostics/probe_qwen_worker_latency.py --package <package> --out <new-dir> --cpu-placement performance --cpu-qos latency --repeats 3 --gate-after
```

200ms remains unachieved. The repaired regression returns typical warm performance
to the prior half-second range; simulator-load tail latency and flight behavior
remain separate qualifications. Future optimization must keep placement/QoS fixed.
