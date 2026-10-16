# D138 saved-input runtime experiment

User authorized local attention/decoding benchmark after D137 research. No flight,
training, AWS, model download, freshness changes or environment installation.

One loaded NF4 Qwen/D207 base, all weights frozen. Four saved contexts: forward,
turn, ascent with brightness variation, and D135 saved forward image/prompt.
Warmup/eligibility excluded.25 alternating-order repeats per context:100 paired
contexts per supported variant. Compare complete four-token actions and decoded
values against baseline within each pair. No cached-image speed shortcut.

Variants: existing default SDPA/dynamic cache; force FlashAttention; force efficient
attention; equivalent grouped-query KV repetition plus forced efficient attention;
static generation cache. Unsupported variants retain complete errors/warnings.
A tiny compiler prerequisite test is separate from model qualification. No GPU
compilation result claimed if this cannot complete. Manual CUDA graphs are not
implemented by this probe. Main process1200s watchdog, all actions discarded.

Then test base planner/direction/monitor with a brief fixed text request and pilot
return, record unchanged tensor versions/frozen state/device placement/memory.
These text role checks do not validate semantic image understanding or mission quality.
Reported p95 is descriptive over repeated saved inputs, not new-camera end-to-end
qualification. No200ms claim unless actually reached end-to-end; never renew old
observations for flight. Do not promote a result just for being faster in one session.
