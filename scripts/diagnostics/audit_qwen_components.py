"""Independent fixed-criterion audit of the four easier numeric missions."""

import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path

from audit_qwen_full_architecture import inspect


def poses(rows):
    ticks = [r for r in rows if r["kind"] == "tick"]
    origin, yaw = ticks[0]["position"], ticks[0]["yaw"]
    result = []
    for row in ticks:
        dx, dy, dz = (row["position"][k]-origin[k] for k in ("x", "y", "z"))
        heading = -math.degrees(math.atan2(math.sin(row["yaw"]-yaw),
                                         math.cos(row["yaw"]-yaw)))
        result.append(dict(forward=dx*math.cos(yaw)+dy*math.sin(yaw),
                           right=dx*math.sin(yaw)-dy*math.cos(yaw), up=dz,
                           heading=heading, displacement=math.sqrt(dx*dx+dy*dy+dz*dz),
                           wall_ns=row["wall_ns"]))
    return result


def movement_checks(rows, case, criteria):
    path = poses(rows)
    maximum = max(p["displacement"] for p in path)
    heading = max(abs(p["heading"]) for p in path)
    result = dict(max_displacement_m=maximum, max_heading_change_deg=heading)
    if case["id"] == "hold":
        result["hold_pass"] = maximum <= criteria["hold_max_displacement_m"] \
            and heading <= criteria["hold_max_heading_drift_deg"] \
            and not any(r["kind"] == "action_consumed" for r in rows)
    if case["id"] == "move_then_turn":
        reached = [p["wall_ns"] for p in path if math.sqrt(
            (p["forward"]-1)**2+p["right"]**2+p["up"]**2) <= criteria["endpoint_tolerance_m"]]
        turns = [p["wall_ns"] for p in path
                 if abs(p["heading"]) > criteria["heading_tolerance_deg"]]
        result["move_before_turn"] = bool(reached and turns and min(reached) < min(turns))
        result["intermediate_advanced"] = any(r["kind"] == "replan" and
            r["reason"] == "intermediate goal reached; advance mission" for r in rows)
        result["sequence_pass"] = result["move_before_turn"] and result["intermediate_advanced"]
    return result


def audit(root, case, criteria):
    folder = root / case["id"]
    rows, component = inspect(folder)
    movement = movement_checks(rows, case, criteria)
    result = json.loads((folder / "result.json").read_text())
    passed = result["task_pass"] and result["fresh_actions"] and result["timing_pass"] \
        and result["collisions"] == 0 and not result["out_of_bounds"]
    passed = passed and movement.get("hold_pass", True) and movement.get("sequence_pass", True)
    return dict(passed=passed, result=result, movement=movement, component=component)


def archive_logs(root, cases):
    manifest = {}
    with zipfile.ZipFile(root / "raw_events.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for case in cases:
            path = root / case["id"] / "events.jsonl"
            relative = path.relative_to(root).as_posix()
            archive.write(path, relative)
            manifest[relative] = dict(bytes=path.stat().st_size,
                                      sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (root / "raw_events_manifest.json").write_text(json.dumps(manifest, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads((args.root / "config.json").read_text())
    audits = {c["id"]: audit(args.root, c, settings["audit_criteria"])
              for c in settings["missions"]}
    (args.root / "component_audit.json").write_text(json.dumps(audits, indent=2))
    archive_logs(args.root, settings["missions"])
    print(json.dumps({name: {k: v for k, v in a.items() if k != "component"}
                      for name, a in audits.items()}, indent=2))


if __name__ == "__main__":
    main()
