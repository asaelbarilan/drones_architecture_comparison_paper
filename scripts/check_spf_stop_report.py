import json
from pathlib import Path

from playwright.sync_api import sync_playwright

out = Path("reports/spf_stop_contract_20260917")
with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://127.0.0.1:8766/spf_stop_contract.html", wait_until="networkidle")
    assert page.locator("article").count() == 7
    assert page.locator("img").evaluate_all(
        "(els)=>els.every(e=>e.complete && e.naturalWidth===224 && e.naturalHeight===224)"
    )
    assert page.locator(".model").count() == 4
    page.locator("#boxes").uncheck()
    assert page.locator(".model").first.evaluate("(e)=>getComputedStyle(e).display") == "none"
    page.locator("#boxes").check()
    assert page.locator(".model").first.evaluate("(e)=>getComputedStyle(e).display") != "none"
    page.screenshot(path=str(out / "DASHBOARD.png"), full_page=True)
    page.locator("#full_close26").scroll_into_view_if_needed()
    page.screenshot(path=str(out / "CLOSEUP_CHECK.png"))
    assert not errors
    (out / "BROWSER_CHECK.json").write_text(
        json.dumps(
            {
                "cards": 7,
                "images_loaded": 7,
                "model_boxes": 4,
                "box_toggle_checks": 2,
                "page_errors": errors,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    browser.close()
print("7 source images, 4 boxes, toggle checks passed; no page errors")
