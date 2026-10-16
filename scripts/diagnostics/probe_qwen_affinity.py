"""D139 reversible CPU-placement experiment, confined to this diagnostic process."""

import argparse
import ctypes
import json
import os
import threading
from ctypes import wintypes
from pathlib import Path

from probe_qwen_kernels import cases_for
from probe_qwen_slow_session import gpu_state, timed
from probe_qwen_stream import save

from uavlab.plugins.inference.shared_qwen import SharedQwenInference

WATCHDOG_SECONDS = 300
MIN_CPU_CLASSES = 2


class Affinity:
    def __init__(self):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.GetCurrentProcess.restype = wintypes.HANDLE
        self.api.GetProcessAffinityMask.argtypes = [wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
        self.api.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        self.handle = self.api.GetCurrentProcess()
        process, system = ctypes.c_size_t(), ctypes.c_size_t()
        if not self.api.GetProcessAffinityMask(self.handle, ctypes.byref(process),
                                             ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        self.original = process.value

    def set(self, mask):
        if not mask or mask & ~self.original:
            raise ValueError("Test mask must be a nonempty subset of original affinity")
        if not self.api.SetProcessAffinityMask(self.handle, mask):
            raise ctypes.WinError(ctypes.get_last_error())

    def cpu(self):
        return self.api.GetCurrentProcessorNumber()


def masks(path, original):
    rows = json.loads(path.read_text())
    if any(row["group"] != 0 for row in rows):
        raise ValueError("Diagnostic only supports this single-group host")
    classes = sorted({row["efficiency_class"] for row in rows})
    if len(classes) < MIN_CPU_CLASSES:
        raise ValueError("No heterogeneous CPU classes identified")
    result = {"all": original}
    for name, value in (("performance", classes[-1]), ("efficiency", classes[0])):
        result[name] = sum(1 << row["logical"] for row in rows
                           if row["efficiency_class"] == value) & original
    return result


def experiment(backend, affinity, settings, out):
    cases = cases_for(backend)
    rows = []
    for block, name in enumerate(("all", "performance", "efficiency", "performance", "all")):
        affinity.set(settings[name])
        timed(backend, cases[0])
        for index, request in enumerate(cases):
            before = affinity.cpu()
            result = timed(backend, request)
            rows.append(dict(block=block, name=name, mask=settings[name], case=index,
                             cpu_before=before, cpu_after=affinity.cpu(), result=result))
            save(out / "calls.json", rows)
        print(json.dumps(dict(block=block, name=name,
                              seconds=result["first_action_s"])), flush=True)


def run(args):
    affinity = Affinity()
    settings = masks(args.topology, affinity.original)
    backend = SharedQwenInference(args.package)
    try:
        backend._load()
        threads = backend.torch.get_num_threads()
        backend.torch.set_num_threads(args.threads)
        save(args.out / "identity.json",
             dict(masks=settings, threads=args.threads, gpu=gpu_state()))
        experiment(backend, affinity, settings, args.out)
        backend.torch.set_num_threads(threads)
    finally:
        affinity.set(affinity.original)
        backend.close()
    save(args.out / "complete.json", dict(affinity_restored=affinity.original))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--topology", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    timer = threading.Timer(WATCHDOG_SECONDS, lambda: os._exit(124))
    timer.daemon = True
    timer.start()
    try:
        run(args)
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
