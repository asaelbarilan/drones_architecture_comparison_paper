"""Inspect D-129 flight UI, key source frames and playback with no inference."""

import argparse
import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--interrupted", action="store_true")
args = parser.parse_args()
variants = ["interrupted_c2"] if args.interrupted else ["c2", "c3"]
OUT = Path("reports/spf_arrival_20260917/browser")
OUT.mkdir(parents=True, exist_ok=True)
checks = []
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8766/spf_arrival.html")
    page.wait_for_function('typeof run !== "undefined" && run && run.frames.length>0')
    for i, variant in enumerate(variants):
        page.locator("#run").select_option(str(i))
        page.locator("#follow").check()
        audit = json.loads((OUT.parent / variant / "AUDIT.json").read_text(encoding="utf-8"))
        closest = page.evaluate("run.frames.reduce((a,b)=>a.distance<b.distance?a:b).t")
        end = page.evaluate("run.frames.at(-1).t")
        first_hold = next(iter(audit.get("braking_holds", [])), end)
        for t in sorted({0, 15, closest, max(0, first_hold - 3), first_hold, end}):
            page.evaluate("t=>{pause();seek(nearest(t),true)}", t)
            page.wait_for_function('document.getElementById("drone").complete')
            frame = page.evaluate("({...current(),name:run.name})")
            rgb = frame.pop("rgb")
            checks.append(frame)
            page.screenshot(path=str(OUT / f"{variant}_t{t:.2f}.png"))
            (OUT / f"{variant}_rgb_t{t:.2f}.png").write_bytes(base64.b64decode(rgb.split(",")[1]))
        page.evaluate("t=>{pause();seek(nearest(t),true)}", max(0, first_hold - 3))
        before = page.evaluate("current().t")
        page.locator("#play").click()
        page.wait_for_function("t=>current().t>t+0.5", arg=before)
        page.evaluate("pause()")
    browser.close()
assert not errors, errors
(OUT / "CHECKS.json").write_text(
    json.dumps(dict(checks=checks, playbacks=len(variants), errors=errors), indent=2),
    encoding="utf-8",
)
print(f"{len(checks)} seeks,{len(variants)} playbacks,no JS errors")
