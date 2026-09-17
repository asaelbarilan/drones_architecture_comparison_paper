# ruff: noqa: E501
"""Build the D-128 saved-frame evidence page, without inference."""

import base64
import hashlib
import html
import json
from pathlib import Path

ROOT = Path("reports/spf_stop_contract_20260917")


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


freeze = read(ROOT / "FREEZE.json")
summary = read(ROOT / "SUMMARY.json")
depth = {r["case"]: r for r in read(ROOT / "DEPTH_CHECK.json")["rows"]}
cases = {c["id"]: c for c in freeze["cases"]}
calls = [read(p) for p in sorted((ROOT / "calls").glob("*.json"))]
assert len(calls) == 9 and all(c["status"] == "complete" for c in calls)
for call in calls:
    source = cases[call["task"]["case"]]
    raw = base64.b64decode(call["body"]["messages"][0]["images"][0])
    assert raw == (ROOT / source["image"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == source["input_sha256"]
    assert json.loads(call["reply"]["message"]["thinking"]) == call["answer"]

cards = []
for cid, c in cases.items():
    bbox = next(r for r in summary["rows"] if r["case"] == cid and r["variant"] == "bbox")
    original = next(
        (r for r in summary["rows"] if r["case"] == cid and r["variant"] == "original"), None
    )
    b = bbox["answer"]["box"]
    image = base64.b64encode((ROOT / c["image"]).read_bytes()).decode()
    rectangle = (
        (
            f'<rect class="model" x="{b[0]}" y="{b[1]}" width="{b[2] - b[0]}" '
            f'height="{b[3] - b[1]}" fill="none" stroke="#62e7ef" stroke-width="6"/>'
        )
        if bbox["answer"]["visible"]
        else ""
    )
    truth_range = c["source_distance_m"]
    truth_text = f"{truth_range:.3f} m" if truth_range is not None else "Not used"
    d = depth.get(cid, {}).get("metric_range_m")
    depth_text = f"{d:.3f} m" if d is not None else "No target point"
    original_text = html.escape(json.dumps(original["answer"])) if original else "Not repeated"
    status = "PASS" if bbox["passed"] else "FAIL — target missed"
    cards.append(f'''<article id="{cid}"><h2>{cid} <small>{status}</small></h2>
      <p>Source frame {c["source_time_s"]:.2f} s · RGB PNG · 224 x 224</p>
      <div class="frame"><img alt="Exact VLM input: {cid}" src="data:image/png;base64,{image}">
      <svg viewBox="0 0 999 999">{rectangle}</svg></div>
      <dl><dt>Goal-center range (evaluation only)</dt><dd>{truth_text}</dd>
      <dt>Visible red width (evaluation only)</dt><dd>{100 * c["visible_width_fraction"]:.1f}%</dd>
      <dt>Range to depth point (offline reconstruction)</dt><dd>{depth_text}</dd></dl>
      <p>Original prompt repeat: <code>{original_text}</code></p>
      <details open><summary>Localization-only answer</summary><pre>{html.escape(json.dumps(bbox["answer"], indent=2, ensure_ascii=False))}</pre></details>
      <details><summary>Original flight answer — preserved</summary><pre>{html.escape(c["source_call"]["response"])}</pre></details></article>''')
page = (
    """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>SPF arrival diagnosis · D-128</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b121c;color:#dce8f2;font:16px/1.5 system-ui}main{max-width:1450px;margin:auto;padding:28px}h1{font-size:30px;margin-bottom:8px}h2{font-size:20px}p{color:#acbdd0}a{color:#62e7ef}.notice,article{background:#142130;border:1px solid #304153;border-radius:12px;padding:20px}.notice{margin:20px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(350px,1fr));gap:18px}.frame{width:100%;max-width:350px;aspect-ratio:1;position:relative;margin:auto}.frame img,.frame svg{position:absolute;width:100%;height:100%}.frame img{image-rendering:pixelated}.hide-boxes .model{display:none}small{display:block;color:#e8c77e;font-size:14px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}dt{color:#a6bcd2;font-size:13px}dd{margin:0 0 8px}label{display:block;padding:12px 0}details{border-top:1px solid #304153;padding-top:10px;margin-top:12px}code{color:#f5d59b}
</style><main><p>UAV LAB / SAVED-FRAME DIAGNOSIS / D-128</p>
<h1>The pillar is localized, but the arrival label stays wrong</h1>
<p>Nine local Qwen3-VL 4B calls · seven saved images · no new flight or deployed policy change</p>
<div class="notice"><strong>What this establishes</strong><ul>
<li>The original prompt repeats distance=3 at 1.61 m and 1.27 m. Localization-only boxes accurately cover the target in both images.</li>
<li>The prompt's 25-35% “very close” width rule is already met at 3.41 m. Image width cannot certify the 2 m arrival requirement.</li>
<li>At the red-filled close-up, localization says no pillar is visible. Overall localization score: 6/7 on these selected cases.</li></ul>
<p>Depth at the predicted image points separates the selected far/near cases, but measures a surface point, not necessarily the task's goal center. This is a diagnostic, not proof of a working STOP controller.</p>
<p><a href="c2_c3_preflight.html#run=c2_visible_preflight_20260916_s1061&t=24">Inspect original C2 flight at 24 s</a> · <a href="../spf_stop_contract_20260917/REPORT.md">Evidence report</a></p></div>
<label><input id="boxes" type="checkbox" checked> Show model bounding boxes (cyan)</label><div class="grid">"""
    + "".join(cards)
    + """</div>
<div class="notice"><h2>Method and limits</h2><p>All nine PNG request payloads match the frozen sources byte for byte. Original prompts, schemas and both raw response channels are archived. The configured JSON channel is thinking. Truth annotations and numerical ranges were not sent to the model. 801 replayed poses and six reconstructed source images match the C2 recording.</p><p>Correction to the earlier interpretation: the request at 26 s already returned distance=5 while its source image was red-filled. That label does not establish that the target had left the camera.</p><p>The localization-only task differs from the combined waypoint task. These selected frames do not establish flight reliability or a causal architectural advantage.</p></div></main>
<script>document.getElementById('boxes').addEventListener('change',e=>document.body.classList.toggle('hide-boxes',!e.target.checked));</script></html>"""
)
Path("reports/debugger/spf_stop_contract.html").write_text(page, encoding="utf-8")
print("Built 7 image cards; all 9 exact request images verified")
