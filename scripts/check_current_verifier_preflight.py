"""Inspect visible-target preflight approaches and compare the final C5 overview."""

import base64
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path("reports/c2_c3_preflight_20260916/browser")
OUT.mkdir(exist_ok=True)
checks = []
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100})
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8766/c2_c3_preflight.html")
    page.wait_for_function('typeof run !== "undefined" && run && run.frames.length>0')
    for i, variant in enumerate(["c2", "c3"]):
        page.locator("#run").select_option(str(i))
        page.locator("#follow").check()
        closest = page.evaluate("run.frames.reduce((a,b)=>a.distance<b.distance?a:b).t")
        end = page.evaluate("run.frames.at(-1).t")
        for t in sorted({0, 15, 20, 25, 40, closest, end}):
            page.evaluate("t=>{pause();seek(nearest(t),true)}", t)
            page.wait_for_function('document.getElementById("drone").complete')
            frame = page.evaluate("({...current(),name:run.name})")
            rgb = frame.pop("rgb")
            checks.append(frame)
            page.screenshot(path=str(OUT / f"{variant}_t{t}.png"))
            (OUT / f"{variant}_rgb_t{t}.png").write_bytes(base64.b64decode(rgb.split(",")[1]))
        page.evaluate("()=>{pause();seek(nearest(15),true)}")
        page.locator("#play").click()
        page.wait_for_function("current().t>15.5")
        page.evaluate("pause()")
    page.goto("http://127.0.0.1:8766/commitment_validation.html")
    page.wait_for_function('typeof run !== "undefined" && run && run.frames.length>0')
    c5 = []
    for i in range(4):
        page.locator("#run").select_option(str(i))
        page.evaluate("()=>{pause();seek(run.frames.length-1,true)}")
        c5.append(page.evaluate("({name:run.name,t:current().t})"))
    browser.close()
assert not errors, errors
(OUT / "CHECKS.json").write_text(
    json.dumps(dict(checks=checks, playbacks=2, errors=errors, c5_overview=c5), indent=2),
    encoding="utf-8",
)
print(f"{len(checks)} preflight seeks,2 playbacks,4 C5 overview selections; no JS errors")
