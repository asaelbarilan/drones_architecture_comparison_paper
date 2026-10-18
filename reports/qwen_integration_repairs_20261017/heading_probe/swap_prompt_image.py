import base64, json, sys
from pathlib import Path
sys.path.insert(0, "scripts/diagnostics")
from probe_pilot_heading import forward
from uavlab.plugins.inference.shared_qwen import SharedQwenInference
R = Path("reports/qwen_integration_repairs_20261017/long_waypoints_v2")
def load(task, rid):
    rows = [json.loads(l) for l in (R/task/"events.jsonl").read_text().splitlines()]
    p = json.loads(next(r for r in rows if r.get("kind")=="submitted" and r.get("request_id")==rid)["prompt"])
    img = base64.b64encode((R/task/f"input_{rid}_0.png").read_bytes()).decode()
    return p, img
vp, vi = load("visible_target", 39)
sp, si = load("turn_search", 95)
b = SharedQwenInference("D:/drone_vla_pilot/release/hf_fresh_d257/model"); b._load()
try:
    cases = {
      "visible prompt + visible image": (vp, vi),
      "visible prompt + search image": (vp, si),
      "search prompt + search image": (sp, si),
      "search prompt + visible image": (sp, vi),
      "search prompt, yaw0 rem[10.2,0,1.2,0] + search image": (dict(sp, state=[0,0,0,0], remaining=[10.2,0,1.2,0]), si),
      "search prompt, rem lateral/yaw zeroed + search image": (dict(sp, remaining=[sp['remaining'][0],0,sp['remaining'][2],0]), si),
    }
    for k,(p,i) in cases.items():
        print(f"{forward(b,p,i):7.3f}  {k}", flush=True)
    print("visible prompt:", vp); print("search prompt:", sp)
finally:
    b.close()
