"""Export every real submitted role prompt and backend token input, without reruns."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def export(root):
    sections = ["# Exact model prompts\n", "One shared Qwen base; pilot uses the trained adapter. "
                "Other roles disable it. No separate system message is supplied.\n"]
    for role, text in json.loads((root / "prompt_templates.json").read_text()).items():
        sections.append(f"## {role} template\n\n```text\n{text}\n```\n")
    sections.append("## Pilot format\n\nThe JSON request is converted by the frozen package codec "
        "to `Current State: {state}, What action should the uav take to {instruction}?`, "
        "with the current image, assistant bounding-box prefix and `Left` progress line. "
        "The archive contains actual input token IDs and decoded strings for ALL roles, "
        "including startup and preflight calls; image-pad tokens are not image pixels.\n")
    for case in json.loads((root / "config.json").read_text())["missions"]:
        sections.extend(case_prompts(root / case["id"]))
    (root / "PROMPTS.md").write_text("\n".join(sections), encoding="utf-8")
    encoded = root / "encoded_prompts.jsonl"
    with zipfile.ZipFile(root / "encoded_prompts.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(encoded, encoded.name)
    manifest = dict(bytes=encoded.stat().st_size,
                    sha256=hashlib.sha256(encoded.read_bytes()).hexdigest(),
                    calls=len(encoded.read_text(encoding="utf-8").splitlines()))
    (root / "encoded_prompts_manifest.json").write_text(json.dumps(manifest, indent=2))
    export_encoded(root, encoded)


def export_encoded(root, encoded):
    sections = ["# Actual decoded token inputs, in backend execution order\n",
                "Includes startup/preflight calls. Tokens are unabridged, including image pads. "
                "Actual camera pixels are preserved in the event archive.\n"]
    for index, line in enumerate(encoded.read_text(encoding="utf-8").splitlines()):
        row = json.loads(line)
        sections.append(f"## {index}: {row['role']}, observation {row['observation_seq']}\n\n"
                        f"```text\n{row['decoded_input']}\n```\n")
    (root / "ENCODED_PROMPTS.md").write_text("\n".join(sections), encoding="utf-8")


def case_prompts(folder):
    rows = [json.loads(line) for line in (folder / "events.jsonl").read_text().splitlines()]
    results = {r["request_id"]: r["payload"] for r in rows if r["kind"] == "result"}
    sections = [f"## Actual calls: {folder.name}\n"]
    for row in rows:
        if row["kind"] != "submitted":
            continue
        identity = row["request_id"]
        sections.append(f"### {identity}: {row['role']} (observation {row['observation_seq']})\n\n"
                        f"```text\n{row['prompt']}\n```\n\n"
                        f"Response: `{json.dumps(results.get(identity, 'streamed actions'))}`\n")
    return sections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    export(parser.parse_args().root)


if __name__ == "__main__":
    main()
