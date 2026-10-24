"""D-186 detector probe, step 2: YOLO-World and OWLv2 on the simulator frames, against truth.

Runs with drone_control's environment, which already has ultralytics, transformers, the
YOLO-World weights and the cached OWLv2 model (nothing is downloaded or installed):

    ../../drone_control/.venv/Scripts/python.exe scripts/diagnostics/probe_detectors.py

For each frame and each truly visible object it asks the detector for the object's text label
and keeps the highest-scoring box: a hit is IoU >= 0.5 with the true box. For the two vehicles
it asks for "overturned car" and checks the box lands on the overturned one, not the upright
one. Warm latency per call is timed on the GPU.
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image

DRONE_CONTROL = Path(__file__).resolve().parents[4] / "drone_control"
YOLO_WORLD = DRONE_CONTROL / "weights" / "yolov8s-world.pt"
OWL = "google/owlv2-base-patch16-ensemble"
PROMPTS = {"red pillar": "red pillar", "blue pillar": "blue pillar",
           "overturned vehicle": "overturned car", "upright vehicle": "upright car"}
HIT_IOU = 0.5
COORD = 1000
WARMUP = 3


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


class YoloWorld:
    name = "YOLO-World-S"

    def __init__(self):
        from ultralytics import YOLO
        # set_classes after the model has moved to the GPU fails (text encoder on the CPU),
        # so each prompt gets its own copy, classes set once before any prediction.
        self.models = {}
        for prompt in PROMPTS.values():
            model = YOLO(str(YOLO_WORLD))
            model.set_classes([prompt])
            self.models[prompt] = model

    def best(self, image, prompt):
        result = self.models[prompt].predict(image, imgsz=640, conf=0.01, verbose=False)[0]
        if len(result.boxes) == 0:
            return None, 0.0
        i = int(result.boxes.conf.argmax())
        x0, y0, x1, y1 = result.boxes.xyxy[i].tolist()
        w, h = image.size
        return [x0 * COORD / w, y0 * COORD / h, x1 * COORD / w, y1 * COORD / h], float(
            result.boxes.conf[i])


class Owl:
    name = "OWLv2-base"

    def __init__(self):
        from transformers import Owlv2ForObjectDetection, Owlv2Processor
        self.processor = Owlv2Processor.from_pretrained(OWL, local_files_only=True)
        self.model = Owlv2ForObjectDetection.from_pretrained(OWL, local_files_only=True)
        self.model = self.model.to("cuda").eval()

    def best(self, image, prompt):
        inputs = self.processor(text=[[prompt]], images=image, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = self.model(**inputs)
        side = max(image.size)  # OWLv2 pads to a square
        sizes = torch.tensor([[side, side]])
        try:  # transformers 4.x name; 5.x renamed it (as drone_control's grounding.py does)
            found = self.processor.post_process_object_detection(
                outputs=outputs, threshold=0.0, target_sizes=sizes)[0]
        except (AttributeError, TypeError):
            found = self.processor.post_process_grounded_object_detection(
                outputs=outputs, threshold=0.0, target_sizes=sizes, text_labels=[[prompt]])[0]
        if len(found["scores"]) == 0:
            return None, 0.0
        i = int(found["scores"].argmax())
        x0, y0, x1, y1 = found["boxes"][i].tolist()
        w, h = image.size
        return [x0 * COORD / w, y0 * COORD / h, x1 * COORD / w, y1 * COORD / h], float(
            found["scores"][i])


def score(detector, frames, root):
    rows, times = [], []
    for frame in frames:
        image = Image.open(root / frame["image"]).convert("RGB")
        for label, truth in frame["boxes"].items():
            start = time.perf_counter()
            box, conf = detector.best(image, PROMPTS[label])
            times.append(time.perf_counter() - start)
            overlap = iou(box, truth) if box else 0.0
            rows.append(dict(image=frame["image"], object=label, iou=round(overlap, 3),
                             hit=overlap >= HIT_IOU, conf=round(conf, 3), box=box))
    return rows, times[WARMUP:]


def summary(name, rows, times):
    pillars = [r for r in rows if "pillar" in r["object"]]
    overturned = [r for r in rows if r["object"] == "overturned vehicle"]
    return dict(detector=name,
                pillar_hits=f"{sum(r['hit'] for r in pillars)}/{len(pillars)}",
                pillar_mean_iou=round(statistics.mean(r["iou"] for r in pillars), 3),
                overturned_hits=f"{sum(r['hit'] for r in overturned)}/{len(overturned)}",
                median_ms=round(1000 * statistics.median(times), 1),
                p95_ms=round(1000 * float(np.percentile(times, 95)), 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--frames", type=Path, default=Path("reports/detector_probe/frames"))
    args = parser.parse_args()
    frames = json.loads((args.frames / "truth.json").read_text())
    report = []
    for make in (YoloWorld, Owl):
        detector = make()
        rows, times = score(detector, frames, args.frames)
        (args.frames.parent / f"{detector.name}.json").write_text(json.dumps(rows, indent=1))
        report.append(summary(detector.name, rows, times))
        del detector
        torch.cuda.empty_cache()
    (args.frames.parent / "summary.json").write_text(json.dumps(report, indent=1))
    for line in report:
        print(line)


if __name__ == "__main__":
    main()
