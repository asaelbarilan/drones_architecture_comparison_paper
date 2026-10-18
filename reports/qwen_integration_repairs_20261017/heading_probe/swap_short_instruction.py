import base64, json, sys
from pathlib import Path
sys.path.insert(0, "scripts/diagnostics")
from probe_pilot_heading import forward
from uavlab.plugins.inference.shared_qwen import SharedQwenInference
R = Path("reports/qwen_integration_repairs_20261017/long_waypoints_v2/turn_search")
rows = [json.loads(l) for l in (R/"events.jsonl").read_text().splitlines()]
subs = [r for r in rows if r.get("kind")=="submitted" and r.get("role")=="pilot" and (R/f"input_{r['request_id']}_0.png").exists()][:6]
b = SharedQwenInference("D:/drone_vla_pilot/release/hf_fresh_d257/model"); b._load()
short = "Fly to the red pillar and stop within 2 metres."
try:
    for r in subs:
        p = json.loads(r["prompt"]); img = base64.b64encode((R/f"input_{r['request_id']}_0.png").read_bytes()).decode()
        s = p["state"]; y0 = 210.5269654699457
        out = dict(
          short_yaw0=forward(b, dict(p, instruction=short, state=[*s[:3], 0.0]), img),
          short_yaw_rebased=forward(b, dict(p, instruction=short, state=[*s[:3], s[3]-y0]), img),
          long_yaw_rebased=forward(b, dict(p, state=[*s[:3], s[3]-y0]), img))
        print(r["request_id"], out, flush=True)
finally:
    b.close()
