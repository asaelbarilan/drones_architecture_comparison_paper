"""Read immutable flight evidence without running a model or simulator."""

import bisect
import json
import math
import zipfile

from PIL import Image

ROLES = ("planner", "direction", "pilot", "monitor")


class Trace:
    def __init__(self, root):
        self.root = root
        with zipfile.ZipFile(root / "raw_events.zip") as archive:
            raw = archive.read("red_pillar/events.jsonl")
            self.rows = [json.loads(s) for s in raw.splitlines()]
        self.ticks = [r for r in self.rows if r["kind"] == "tick"]
        self.start = self.ticks[0]["wall_ns"]
        self.times = [self.seconds(r) for r in self.ticks]
        self.duration = max(self.seconds(r) for r in self.rows if "wall_ns" in r)
        truth = json.loads((root / "red_pillar/evaluator_only.json").read_text())
        self.target = truth["object_position"]
        self.distances = [math.dist(list(r["position"][k] for k in ("x", "y", "z")), self.target)
                          for r in self.ticks]
        self.requests = [r for r in self.rows if r["kind"] == "submitted"]
        self.done = {r["request_id"]: self.seconds(r) for r in self.rows if r["kind"] == "done"}
        self.photos = self.load_photos()

    def seconds(self, row):
        return (row["wall_ns"]-self.start)/1e9

    def load_photos(self):
        folder = self.root / "red_pillar"
        photos = [(0.0, "initial camera", Image.open(folder / "initial_camera.png").convert("RGB"))]
        for r in self.requests:
            if r.get("image_files"):
                photos.append((self.seconds(r), r["role"],
                               Image.open(folder / r["image_files"][0]).convert("RGB")))
        final = Image.open(folder / "final_camera.png").convert("RGB")
        photos.append((self.duration, "final camera", final))
        return sorted(photos, key=lambda p: p[0])

    def at(self, seconds):
        index = max(0, bisect.bisect_right(self.times, seconds)-1)
        photo = max((p for p in self.photos if p[0] <= seconds), key=lambda p: p[0])
        return index, photo

    def role_state(self, role, seconds):
        requests = [r for r in self.requests if r["role"] == role and self.seconds(r) <= seconds]
        active = any(self.done[r["request_id"]] > seconds for r in requests)
        return len(requests), active

    def consumed(self, seconds):
        return sum(r["kind"] == "action_consumed" and self.seconds(r) <= seconds for r in self.rows)

    def caption(self, role, seconds, fallback):
        rows = [r for r in self.rows if "wall_ns" in r and self.seconds(r) <= seconds]
        if role == "direction":
            boxes = [r for r in rows if r["kind"] == "grounding_validated"]
            return f"Last box: {boxes[-1]['payload']['target']['box']}" if boxes else fallback
        if role == "pilot":
            actions = [r for r in rows if r["kind"] == "action_consumed"]
            if actions:
                forward, right, up, _ = actions[-1]["packet"]["step_fru_m_yaw_rad"]
                return f"Last move F {forward:+.2f} / R {right:+.2f} / U {up:+.2f} m"
        results = [r for r in rows if r["kind"] == "result" and r["role"] == role]
        if results and role == "monitor":
            return "Recorded verdict: " + json.loads(results[-1]["payload"])["status"]
        if results and role == "planner":
            return "Committed target: red pillar / approach + stop"
        return fallback
