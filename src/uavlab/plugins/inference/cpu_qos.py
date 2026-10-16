"""Windows execution-speed hint scoped to the current inference process.

HighQoS asks Windows to treat this work as latency-sensitive. It does not change
scheduler priority, the machine power plan, timer policy, or another process.
"""

import ctypes
import sys
from contextlib import contextmanager
from ctypes import wintypes
from typing import ClassVar

POWER_CLASS = 4
EXECUTION_SPEED = 1


class PowerState(ctypes.Structure):
    _fields_: ClassVar = [("version", wintypes.ULONG), ("control", wintypes.ULONG),
                         ("state", wintypes.ULONG)]


class WindowsExecutionQoS:
    def __init__(self):
        self.api = ctypes.WinDLL("kernel32", use_last_error=True)
        self.api.GetCurrentProcess.restype = wintypes.HANDLE
        self.handle = self.api.GetCurrentProcess()
        for name in ("GetProcessInformation", "SetProcessInformation"):
            getattr(self.api, name).argtypes = [wintypes.HANDLE, ctypes.c_int,
                                               ctypes.c_void_p, wintypes.DWORD]

    def get(self):
        value = PowerState(1, 0, 0)
        if not self.api.GetProcessInformation(self.handle, POWER_CLASS, ctypes.byref(value),
                                              ctypes.sizeof(value)):
            raise ctypes.WinError(ctypes.get_last_error())
        return dict(control=value.control, state=value.state)

    def set(self, value):
        native = PowerState(1, value["control"], value["state"])
        if not self.api.SetProcessInformation(self.handle, POWER_CLASS, ctypes.byref(native),
                                              ctypes.sizeof(native)):
            raise ctypes.WinError(ctypes.get_last_error())


def latency_state(original):
    return dict(control=original["control"] | EXECUTION_SPEED,
                state=original["state"] & ~EXECUTION_SPEED)


@contextmanager
def execution_qos(policy="inherit", factory=WindowsExecutionQoS):
    if policy == "inherit":
        yield dict(policy=policy)
        return
    if policy != "latency" or sys.platform != "win32":
        raise ValueError("Latency CPU QoS is an opt-in Windows-only policy")
    native = factory()
    original = native.get()
    try:
        native.set(latency_state(original))
        selected = native.get()
        if selected != latency_state(original):
            raise RuntimeError("Windows did not apply the execution-speed QoS request")
        yield dict(policy=policy, original=original, selected=selected)
    finally:
        native.set(original)
