"""Read-only sampled GPU telemetry, timestamped against runtime role events."""

import json
import subprocess
import threading
import time


class GpuTrace:
    def __init__(self, out):
        self.out = out
        self.process = self.thread = None

    def __enter__(self):
        fields = "memory.used,memory.total,utilization.gpu,utilization.memory,power.draw"
        self.process = subprocess.Popen(
            ["nvidia-smi", "--query-gpu="+fields, "--format=csv,noheader,nounits", "-lms", "200"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.thread = threading.Thread(target=self.read, daemon=True)
        self.thread.start()
        return self

    def read(self):
        keys = ("used_mib", "total_mib", "gpu_percent", "memory_percent", "power_w")
        with (self.out / "gpu_samples.jsonl").open("w") as stream:
            for line in self.process.stdout:
                row = dict(wall_ns=time.perf_counter_ns(), raw=line.strip())
                try:
                    row.update(dict(zip(keys, map(float, line.strip().split(",")), strict=True)))
                except ValueError:
                    row["parse_error"] = True
                stream.write(json.dumps(row)+"\n")
                stream.flush()

    def __exit__(self, *exc):
        self.process.terminate()
        self.process.wait(timeout=10)
        self.thread.join(timeout=10)
