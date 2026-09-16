"""Inspect both matched240s trajectories and actual decision sources in Edge."""

import argparse
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--out", default="reports/commitment_pair_20260916")
parser.add_argument("--page", default="commitment_240")
args = parser.parse_args()
out = Path(args.out) / "browser"
out.mkdir(parents=True, exist_ok=True)
errors = []
checks = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:8766/{args.page}_comparison.html")
    page.wait_for_function('typeof run !== "undefined" && run && run.frames.length>0')
    for i, variant in enumerate(["off", "on"]):
        page.locator("#run").select_option(str(i))
        page.locator("#follow").check()
        end = page.evaluate("run.frames.at(-1).t")
        audit = json.loads((out.parent / variant / "AUDIT.json").read_text(encoding="utf-8"))
        times = [0, 26, 45, 60, 90, 120, 180, 240, audit["closest_s"], end]
        for lease in audit["leases"].values():
            times += [lease["activation_s"], lease["activation_s"] + 10, lease["deadline_s"]]
        for t in sorted(set(t for t in times if t <= end)):
            page.evaluate("(t)=>{pause();seek(nearest(t),true)}", t)
            page.wait_for_function('document.getElementById("drone").complete')
            row = page.evaluate("({...current(),name:run.name})")
            rgb = row.pop("rgb")
            checks.append(row)
            page.screenshot(path=str(out / f"{variant}_t{t}.png"))
            (out / f"{variant}_rgb_t{t}.png").write_bytes(base64.b64decode(rgb.split(",")[1]))
        page.evaluate(
            "()=>{pause();$('follow').checked=false;"
            "selectDecision(run.decisions.findLastIndex(d=>d.role==='monitor'),true)}"
        )
        page.screenshot(path=str(out / f"{variant}_monitor.png"))
        page.evaluate("()=>{pause();seek(nearest(20),true)}")
        page.locator("#play").click()
        page.wait_for_function("current().t>20")
        page.evaluate("pause()")
    browser.close()
assert not errors, errors
(out / "CHECKS.json").write_text(
    json.dumps(dict(checks=checks, playbacks=2, errors=errors), indent=2), encoding="utf-8"
)
print(f"{len(checks)} seeks, two playbacks, no JS errors")
