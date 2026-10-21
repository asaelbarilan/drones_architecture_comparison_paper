"""Download the papers a research pass cited into `papers/<topic>/`.

A link in a doc rots and cannot be read offline. The `/research` skill requires
every cited paper to land here so the folder is a reading list the user can open
without asking me for it.

    python scripts/fetch_papers.py --topic search \
        2024_FALCON_coverage-path-guidance=https://arxiv.org/abs/2407.00577 \
        2021_FUEL_incremental-frontier=https://arxiv.org/abs/2010.11561

arXiv `/abs/` and `/html/` URLs are rewritten to `/pdf/` automatically. Anything
that does not return a PDF is reported and skipped — a paywalled paper should be
noted in the topic README, not replaced by whatever HTML the publisher served.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UA = "Mozilla/5.0 (compatible; uav-arch-lab-research/1.0)"


def to_pdf_url(url: str) -> str:
    """arXiv serves the same paper at /abs/, /html/ and /pdf/ — we want the PDF."""
    m = re.match(r"https?://(?:www\.)?arxiv\.org/(?:abs|html|pdf)/([^/?#]+?)(?:v\d+)?(?:\.pdf)?/?$", url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}"
    m = re.match(r"https?://ar5iv\.labs\.arxiv\.org/html/([^/?#]+)", url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}"
    return url


def fetch(name: str, url: str, out_dir: str) -> tuple[bool, str]:
    pdf_url = to_pdf_url(url)
    path = os.path.join(out_dir, name if name.endswith(".pdf") else name + ".pdf")
    if os.path.exists(path) and os.path.getsize(path) > 10_000:
        return True, f"have  {os.path.basename(path)}"
    try:
        req = urllib.request.Request(pdf_url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            head = r.read(5)
            if head != b"%PDF-":
                return False, f"SKIP  {name}: not a PDF (paywalled?) {pdf_url}"
            body = head + r.read()
    except Exception as exc:
        return False, f"SKIP  {name}: {type(exc).__name__} {exc}  {pdf_url}"
    with open(path, "wb") as fh:
        fh.write(body)
    return True, f"got   {os.path.basename(path)}  ({len(body)/1e6:.1f} MB)"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", required=True,
                    help="folder under papers/, e.g. search, detection, mapping")
    ap.add_argument("papers", nargs="+", metavar="NAME=URL",
                    help="<year>_<acronym>_<short-title>=<url>")
    args = ap.parse_args()

    out_dir = os.path.join(ROOT, "papers", args.topic)
    os.makedirs(out_dir, exist_ok=True)

    failures = 0
    for item in args.papers:
        if "=" not in item:
            print(f"SKIP  {item}: expected NAME=URL")
            failures += 1
            continue
        name, url = item.split("=", 1)
        ok, msg = fetch(name, url, out_dir)
        print(msg)
        failures += 0 if ok else 1

    print(f"\n-> {out_dir}")
    if failures:
        print(f"{failures} not downloaded — note them in the topic README as paywalled.")
    sys.exit(0)


if __name__ == "__main__":
    main()
