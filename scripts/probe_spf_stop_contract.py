"""D-128: nine fixed saved-image calls to isolate the SPF near-label failure."""

import argparse
import base64
import hashlib
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
from PIL import Image

OUT = Path("reports/spf_stop_contract_20260917")
SOURCE = Path("reports/c2_c3_preflight_20260916/c2")


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def prepare():
    assert not (OUT / "FREEZE.json").exists()
    p = read(SOURCE / "manifest.json")["architecture_config"]["inference"]["params"]
    diagnostic = read(Path("reports/localization_formats_20260914/FREEZE.json"))["variants"]["bbox"]
    diagnostic["prompt"] = diagnostic["prompt"].replace("red tower", "red pillar")
    frames = {f["observation_seq"]: f for f in read(SOURCE / "replay.json")["frames"]}
    cases = []
    for name, folder, t in [
        ("far", SOURCE, 0),
        ("width_threshold", SOURCE, 20),
        ("close24", SOURCE, 24),
        ("close25", SOURCE, 25),
        ("full_close26", SOURCE, 26),
        ("absent", SOURCE, 40),
        ("green", Path("reports/commitment_validation_20260916/s1060/on"), 53),
    ]:
        calls = [read(f) for f in (folder / "debug/calls").glob("*.json")]
        call = next(c for c in calls if c["role"] == "policy" and c["started_t_sim_ns"] / 1e9 == t)
        raw = (folder / call["image_files"][0]).read_bytes()
        image_path = OUT / "images" / f"{name}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(raw)
        pixels = np.asarray(Image.open(image_path).convert("RGB"))
        # Evaluation-only red annotation; NEVER included in any inference request.
        ys, xs = np.where((pixels[:, :, 0] > 150) & (pixels[:, :, 1] < 90) & (pixels[:, :, 2] < 90))
        box = (
            [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]
            if len(xs)
            else None
        )
        frame = frames.get(call["observation_seq"]) if folder == SOURCE else None
        case = dict(
            id=name,
            source=str(folder),
            source_call=call,
            input_sha256=hashlib.sha256(raw).hexdigest(),
            image=f"images/{name}.png",
            annotation_box_pixels=box,
            visible_width_fraction=(box[2] - box[0]) / pixels.shape[1] if box else 0,
            source_time_s=frame["t"] if frame else 52.95,
            source_distance_m=frame["distance"] if frame else None,
        )
        cases.append(case)
    tasks = [dict(case=n, variant="original") for n in ["close24", "close25"]]
    tasks += [dict(case=c["id"], variant="bbox") for c in cases]
    write(
        OUT / "FREEZE.json",
        dict(
            decision="D-128",
            inference=p,
            cases=cases,
            tasks=tasks,
            diagnostic=diagnostic,
            calls_budget=9,
            hypothesis=(
                "Original numeric labels may fail despite usable visual localization. "
                "Box width is not assumed to certify 2m arrival."
            ),
            criteria=(
                "Original same-source label reproduction; bbox visibility correct, "
                "IoU>=0.5 and center in annotation for positives, absent for negatives. "
                "Examine source metric range separately, never provide it to model. "
                "No flights or deployed policy changes."
            ),
        ),
    )
    write(OUT / "STATE.json", dict(status="frozen", completed=0))
    print([(c["id"], c["visible_width_fraction"], c["source_distance_m"]) for c in cases])


def call_api(path, body=None):
    req = urllib.request.Request(
        "http://127.0.0.1:11435" + path,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as reply:
        return json.load(reply)


def run():
    f = read(OUT / "FREEZE.json")
    p = f["inference"]
    model = next(m for m in call_api("/api/tags")["models"] if m["name"] == p["model_id"])
    assert model["digest"] == p["expected_digest"]
    write(OUT / "MODEL.json", model)
    cases = {c["id"]: c for c in f["cases"]}
    for i, task in enumerate(f["tasks"]):
        c = cases[task["case"]]
        variant = task["variant"]
        dest = OUT / "calls" / f"{i + 1:02}_{c['id']}_{variant}.json"
        assert not dest.exists(), "No implicit retries or overwrites"
        raw = (OUT / c["image"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == c["input_sha256"]
        prompt = c["source_call"]["prompt"] if variant == "original" else f["diagnostic"]["prompt"]
        schema = (
            c["source_call"]["response_schema"]
            if variant == "original"
            else f["diagnostic"]["schema"]
        )
        body = dict(
            model=p["model_id"],
            messages=[dict(role="user", content=prompt, images=[base64.b64encode(raw).decode()])],
            stream=False,
            think=p["think"],
            keep_alive=p["keep_alive"],
            format=schema,
            options=dict(
                temperature=p["temperature"],
                seed=p["sampling_seed"],
                num_ctx=p["num_ctx"],
                num_predict=p["num_predict"],
            ),
        )
        write(dest, dict(status="started", task=task, body=body, image_sha256=c["input_sha256"]))
        started = time.monotonic()
        reply = call_api("/api/chat", body)
        answer = json.loads(reply["message"][p["response_channel"]])
        resident = next(m for m in call_api("/api/ps")["models"] if m["name"] == p["model_id"])
        assert resident["digest"] == p["expected_digest"] and resident["size_vram"] > 0
        write(
            dest,
            dict(
                status="complete",
                task=task,
                body=body,
                image_sha256=c["input_sha256"],
                reply=reply,
                answer=answer,
                wall_s=time.monotonic() - started,
                residency=resident,
            ),
        )
        write(OUT / "STATE.json", dict(status="running", completed=i + 1))
        print(task, answer, flush=True)
    write(
        OUT / "STATE.json", dict(status="calls_complete_audit_pending", completed=len(f["tasks"]))
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prepare", "run"])
    args = parser.parse_args()
    prepare() if args.mode == "prepare" else run()
