"""Local preflight resource gate after the D-129 allocation failure; no model calls."""

import ctypes
import json
import math
import subprocess
from datetime import datetime, timezone


class MemoryStatus(ctypes.Structure):
    _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong)] + [
        (name, ctypes.c_ulonglong)
        for name in (
            "total_physical",
            "available_physical",
            "total_pagefile",
            "available_pagefile",
            "total_virtual",
            "available_virtual",
            "available_extended",
        )
    ]


def snapshot():
    status = MemoryStatus()
    status.length = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise OSError("Cannot read current Windows memory availability")
    command = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    # This workstation has one GPU. Do not aggregate unrelated device capacity.
    values = command.stdout.strip().splitlines()
    if len(values) != 1:
        raise RuntimeError("Resource gate requires one explicitly identified GPU")
    return dict(
        checked_at=datetime.now(timezone.utc).isoformat(),
        available_physical_gib=status.available_physical / 2**30,
        available_commit_gib=status.available_pagefile / 2**30,
        available_gpu_gib=float(values[0]) / 1024,
    )


def check_headroom(sample, *, loaded=False):
    limits = (1.5, 2.0, 0.75) if loaded else (8.0, 10.0, 5.5)
    keys = ("available_physical_gib", "available_commit_gib", "available_gpu_gib")
    shortfalls = []
    for key, limit in zip(keys, limits, strict=True):
        value = sample.get(key)
        if not isinstance(value, int | float) or not math.isfinite(value) or value < limit:
            shortfalls.append(dict(resource=key, available_gib=value, required_gib=limit))
    return dict(
        ready=not shortfalls,
        phase="loaded" if loaded else "before_load",
        snapshot=sample,
        shortfalls=shortfalls,
    )


if __name__ == "__main__":
    result = check_headroom(snapshot())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["ready"] else 2)
