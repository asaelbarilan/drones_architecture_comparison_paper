"""Opt-in Windows worker placement; never changes another process or power plan."""

import ctypes
import struct
import sys
from contextlib import contextmanager
from ctypes import wintypes

CPU_SET_TYPE = 0
CPU_SET_BYTES = 32
HEADER_BYTES = 8


def parse_cpu_sets(raw):
    rows, offset = [], 0
    while offset < len(raw):
        if len(raw)-offset < HEADER_BYTES:
            raise ValueError("Truncated CPU-set header")
        size, kind = struct.unpack_from("<II", raw, offset)
        if size < HEADER_BYTES or offset+size > len(raw):
            raise ValueError("Invalid CPU-set size")
        if kind == CPU_SET_TYPE:
            if size < CPU_SET_BYTES:
                raise ValueError("Truncated CPU-set information")
            group, logical = struct.unpack_from("<HB", raw, offset+12)
            rows.append((group, logical, raw[offset+18]))
        offset += size
    return rows


def performance_mask(rows, allowed):
    if not rows or any(group != 0 for group, _, _ in rows):
        raise ValueError("CPU placement requires one known Windows processor group")
    highest = max(level for _, _, level in rows)
    mask = 0
    for _, logical, level in rows:
        if level == highest:
            mask |= 1 << logical
    mask &= allowed
    if not mask:
        raise ValueError("No performance CPU is allowed by the inherited affinity")
    return mask


class WindowsAffinity:
    def __init__(self):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.GetCurrentProcess.restype = wintypes.HANDLE
        self.handle = self.api.GetCurrentProcess()
        self.api.GetProcessAffinityMask.argtypes = [wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_size_t)]
        self.api.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
        self.api.GetSystemCpuSetInformation.argtypes = [ctypes.c_void_p, wintypes.ULONG,
            ctypes.POINTER(wintypes.ULONG), wintypes.HANDLE, wintypes.ULONG]

    def get(self):
        process, system = ctypes.c_size_t(), ctypes.c_size_t()
        if not self.api.GetProcessAffinityMask(self.handle, ctypes.byref(process),
                                             ctypes.byref(system)):
            raise ctypes.WinError(ctypes.get_last_error())
        return process.value

    def set(self, mask):
        if not self.api.SetProcessAffinityMask(self.handle, mask):
            raise ctypes.WinError(ctypes.get_last_error())

    def topology(self):
        length = wintypes.ULONG()
        query = self.api.GetSystemCpuSetInformation
        query(None, 0, ctypes.byref(length), self.handle, 0)
        if not length.value:
            raise ctypes.WinError(ctypes.get_last_error())
        buffer = ctypes.create_string_buffer(length.value)
        if not query(buffer, length.value, ctypes.byref(length), self.handle, 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return parse_cpu_sets(buffer.raw[:length.value])


@contextmanager
def placed_cpu(policy="inherit", factory=WindowsAffinity):
    if policy == "inherit":
        yield dict(policy=policy)
        return
    if policy != "performance" or sys.platform != "win32":
        raise ValueError("Performance CPU placement is an opt-in Windows-only policy")
    affinity = factory()
    original = affinity.get()
    selected = performance_mask(affinity.topology(), original)
    try:
        affinity.set(selected)
        yield dict(policy=policy, original_mask=original, selected_mask=affinity.get())
    finally:
        affinity.set(original)
