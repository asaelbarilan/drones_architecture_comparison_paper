"""D139 stage/host isolation on saved inputs; no action execution or training."""

import argparse
import cProfile
import json
import os
import pstats
import subprocess
import threading
import time
from collections import Counter
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from probe_qwen_kernels import cases_for
from probe_qwen_stream import measure, save

from uavlab.plugins.inference.shared_qwen import SharedQwenInference

WATCHDOG_SECONDS = 480
REPEATS = 4
MICRO_REPEATS = 100
MICRO_EXPECTED = 2


def gpu_state():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=timestamp,pstate,utilization.gpu,clocks.sm,clocks.mem,"
         "temperature.gpu,power.draw,memory.used", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=10)
    return result.stdout.strip()


def timed(backend, request):
    before = time.process_time()
    result = measure(backend, request, "first_action")
    result["process_cpu_s"] = time.process_time() - before
    return result


def repeat(backend, cases, out):
    original = backend.torch.get_num_threads()
    rows = []
    for threads in (original, 1, original):
        backend.torch.set_num_threads(threads)
        timed(backend, cases[0])
        for iteration in range(REPEATS):
            for index, request in enumerate(cases):
                result = timed(backend, request)
                rows.append(dict(threads=threads, iteration=iteration, case=index,
                                 result=result))
                save(out / "calls.json", rows)
            print(json.dumps(dict(threads=threads, calls=len(rows),
                                  seconds=result["first_action_s"])), flush=True)
    return rows


def microbench(torch):
    sample = torch.ones(4096, device="cuda")
    target = torch.empty_like(sample)
    for _ in range(MICRO_REPEATS):
        torch.add(sample, 1, out=target)
    torch.cuda.synchronize()
    start = time.perf_counter()
    for _ in range(MICRO_REPEATS):
        torch.add(sample, 1, out=target)
    torch.cuda.synchronize()
    eager = time.perf_counter()-start
    result = dict(eager_100_add_s=eager)
    try:
        graph = torch.cuda.CUDAGraph()
        with torch.cuda.graph(graph):
            torch.add(sample, 1, out=target)
        start = time.perf_counter()
        for _ in range(MICRO_REPEATS):
            graph.replay()
        torch.cuda.synchronize()
        result.update(graph_100_add_s=time.perf_counter()-start,
                      graph_result_correct=bool(torch.all(target == MICRO_EXPECTED)))
    except Exception as error:
        result["graph_error"] = repr(error)
    return result


class StageTrace:
    def __init__(self, torch):
        self.torch = torch
        self.rows = []
        self.pending = {}
        self.handles = []

    def before(self, name):
        def hook(module, args, kwargs):
            event = self.torch.cuda.Event(enable_timing=True)
            event.record()
            self.pending[name] = (time.perf_counter(), event)
        return hook

    def after(self, name):
        def hook(module, args, output):
            start, event = self.pending.pop(name)
            end = self.torch.cuda.Event(enable_timing=True)
            end.record()
            self.rows.append(dict(name=name, host_s=time.perf_counter()-start,
                                  start=event, end=end))
        return hook

    def attach(self, model):
        classes = {"Qwen3VLModel", "Qwen3VLVisionModel", "Qwen3VLTextModel"}
        for name, module in model.named_modules():
            if type(module).__name__ in classes or name.endswith("lm_head"):
                self.handles.append(module.register_forward_pre_hook(
                    self.before(name), with_kwargs=True))
                self.handles.append(module.register_forward_hook(self.after(name)))

    def finish(self):
        self.torch.cuda.synchronize()
        for handle in self.handles:
            handle.remove()
        return [dict(name=r["name"], host_s=r["host_s"],
                     device_span_ms=r["start"].elapsed_time(r["end"])) for r in self.rows]


def stage_probe(backend, request, out):
    trace = StageTrace(backend.torch)
    trace.attach(backend.model)
    try:
        result = timed(backend, request)
    finally:
        rows = trace.finish()
    save(out / "stages.json", dict(result=result, stages=rows,
         note="Nested spans; event intervals include host submission gaps, not kernel busy sum."))


def profiles(backend, request, out):
    profiler = cProfile.Profile()
    profiler.enable()
    result = timed(backend, request)
    profiler.disable()
    with (out / "python_profile.txt").open("w") as stream:
        pstats.Stats(profiler, stream=stream).sort_stats("cumtime").print_stats(45)
    save(out / "python_profile_result.json", result)
    torch = backend.torch
    activities = [torch.profiler.ProfilerActivity.CPU, torch.profiler.ProfilerActivity.CUDA]
    with torch.profiler.profile(activities=activities, record_shapes=True) as prof:
        timed(backend, request)
    averages = prof.key_averages()
    for key in ("self_cpu_time_total", "self_cuda_time_total"):
        table = averages.table(sort_by=key, row_limit=35)
        (out / f"profile_{key}.txt").write_text(
            "\n".join(line.rstrip() for line in table.splitlines()).rstrip()+"\n")


def run(args):
    backend = SharedQwenInference(args.package)
    try:
        start = time.perf_counter()
        backend._load()
        versions = [(n, p._version) for n, p in backend.model.named_parameters()]
        cases = cases_for(backend)
        save(args.out / "identity.json", dict(
            load_s=time.perf_counter()-start, torch=backend.torch.__version__,
            threads=backend.torch.get_num_threads(), gpu=gpu_state(),
            devices=dict(Counter(str(p.device) for p in backend.model.parameters()))))
        save(args.out / "cold.json", timed(backend, cases[0]))
        save(args.out / "micro.json", microbench(backend.torch))
        repeat(backend, cases, args.out)
        stage_probe(backend, cases[0], args.out)
        if not args.no_profile:
            profiles(backend, cases[0], args.out)
        save(args.out / "complete.json", dict(
            gpu=gpu_state(), frozen=all(not p.requires_grad for p in backend.model.parameters()),
            versions_unchanged=versions == [(n, p._version)
                                           for n, p in backend.model.named_parameters()]))
    finally:
        backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-profile", action="store_true")
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
