"""D148 measured GPU activity, role behavior and unchanged trajectory comparison."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from compare_qwen_visual import read_episode, role_evidence


def statistics(samples):
    if not samples:
        return dict(samples=0)
    return dict(samples=len(samples), memory_peak_mib=max(s["used_mib"] for s in samples),
                gpu_mean_percent=float(np.mean([s["gpu_percent"] for s in samples])),
                gpu_max_percent=max(s["gpu_percent"] for s in samples),
                gpu_median_percent=float(np.median([s["gpu_percent"] for s in samples])))


def telemetry(root, rows):
    samples = [json.loads(s) for s in (root / "gpu_samples.jsonl").read_text().splitlines()]
    samples = [s for s in samples if "gpu_percent" in s]
    ticks = [r["wall_ns"] for r in rows if r["kind"] == "tick"]
    intervals = []
    starts = {r["request_id"]: r for r in rows if r["kind"] == "submitted"}
    for row in rows:
        if row["kind"] == "done" and row["request_id"] in starts:
            start = starts[row["request_id"]]
            intervals.append((start["role"], start["wall_ns"], row["wall_ns"]))
    result = dict(all=statistics(samples),
                  flight=statistics([s for s in samples if ticks[0] <= s["wall_ns"] <= ticks[-1]]))
    for role in ("planner", "direction", "pilot", "monitor"):
        active = [s for s in samples if any(r == role and a <= s["wall_ns"] <= b
                                           for r, a, b in intervals)]
        result[role] = statistics(active)
    result["metric_note"] = "NVML time busy, not SM occupancy; role windows include CPU work."
    return samples, result


def draw(root, samples):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), layout="constrained")
    runs = ((Path("reports/qwen_visual_object_20261017/real_v2"), "D146"),
            (Path("reports/qwen_grounding_fix_20261017/real_v3"), "D147"), (root, "D148"))
    for folder, label in runs:
        _, times, distance = read_episode(folder)
        axes[0].plot(times, distance, label=label)
    axes[0].axhline(1.5, c="black", ls="--", label="Unchanged success threshold")
    axes[0].set(xlabel="Flight seconds", ylabel="Object distance (m)", title="Actual approaches")
    axes[0].legend()
    start = samples[0]["wall_ns"]
    axes[1].plot([(s["wall_ns"]-start)/1e9 for s in samples],
                 [s["gpu_percent"] for s in samples])
    axes[1].set(xlabel="Seconds including model load/preflight", ylabel="GPU busy (%)",
                title="NVIDIA telemetry (200 ms polling)", ylim=(0, 100))
    fig.savefig(root.parent / "comparison_gpu.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    root = parser.parse_args().root
    rows, _, _ = read_episode(root)
    samples, metrics = telemetry(root, rows)
    (root / "gpu_summary.json").write_text(json.dumps(metrics, indent=2))
    (root / "role_evidence.json").write_text(json.dumps(role_evidence(rows), indent=2))
    raw = root / "gpu_samples.jsonl"
    with zipfile.ZipFile(root / "gpu_samples.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(raw, raw.name)
    (root / "gpu_manifest.json").write_text(json.dumps(dict(
        bytes=raw.stat().st_size, sha256=hashlib.sha256(raw.read_bytes()).hexdigest()), indent=2))
    draw(root, samples)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
