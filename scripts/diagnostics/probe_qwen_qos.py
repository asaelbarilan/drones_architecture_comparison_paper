"""Test Windows execution-speed QoS only for this saved-input diagnostic process."""

import argparse
import ctypes
import os
import threading
from ctypes import wintypes
from pathlib import Path
from typing import ClassVar

from probe_qwen_regression import inputs
from probe_qwen_slow_session import timed
from probe_qwen_stream import save

from uavlab.plugins.inference.cpu_placement import WindowsAffinity, performance_mask
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

POWER_CLASS = 4
REPEATS = 5


class PowerState(ctypes.Structure):
    _fields_: ClassVar = [("version", wintypes.ULONG), ("control", wintypes.ULONG),
                         ("state", wintypes.ULONG)]


class Quality:
    def __init__(self, affinity):
        self.api, self.handle = affinity.api, affinity.handle
        for name in ("GetProcessInformation", "SetProcessInformation"):
            getattr(self.api, name).argtypes = [wintypes.HANDLE, ctypes.c_int,
                                               ctypes.c_void_p, wintypes.DWORD]
        self.original = self.get()

    def get(self):
        value = PowerState(1, 0, 0)
        if not self.api.GetProcessInformation(self.handle, POWER_CLASS, ctypes.byref(value),
                                              ctypes.sizeof(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    def set(self, high):
        value = PowerState(1, self.original.control | 1, self.original.state & ~1)
        if not high:
            value = self.original
        if not self.api.SetProcessInformation(self.handle, POWER_CLASS, ctypes.byref(value),
                                              ctypes.sizeof(value)):
            raise ctypes.WinError(ctypes.get_last_error())


def experiment(backend, quality, out):
    cases, rows = inputs(backend), []
    for block, high in enumerate((False, True, False, True, False)):
        quality.set(high)
        timed(backend, cases["new"])
        for repeat in range(REPEATS):
            for case, request in cases.items():
                result = timed(backend, request)
                rows.append(dict(block=block, high=high, repeat=repeat, case=case, result=result))
                save(out / "calls.json", rows)
        print(f"block={block} high={high} last_s={result['first_action_s']}", flush=True)


def run(args):
    affinity = WindowsAffinity()
    original = affinity.get()
    quality = Quality(affinity)
    backend = SharedQwenInference(args.package)
    try:
        affinity.set(performance_mask(affinity.topology(), original))
        backend._load()
        save(args.out / "identity.json", dict(original_control=quality.original.control,
             original_state=quality.original.state, mask=affinity.get(),
             threads=backend.torch.get_num_threads()))
        experiment(backend, quality, args.out)
    finally:
        quality.set(False)
        affinity.set(original)
        backend.close()
    restored = quality.get()
    save(args.out / "complete.json", dict(mask=affinity.get(),
         control=restored.control, state=restored.state))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(300, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        run(args)
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
