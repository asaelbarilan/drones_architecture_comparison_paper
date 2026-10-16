"""D140 saved-input host scheduling experiment; one model, reversible changes."""

import argparse
import json
import os
import threading
import time
from pathlib import Path

from probe_qwen_regression import inputs
from probe_qwen_slow_session import gpu_state, timed
from probe_qwen_stream import save

from uavlab.plugins.inference.cpu_placement import WindowsAffinity, performance_mask
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

REPEATS = 4


def blocks(mask, threads):
    cpus = [1 << i for i in range(mask.bit_length()) if mask & (1 << i)]
    return [("performance_original", mask, threads), ("performance_one_thread", mask, 1),
            ("one_sibling_per_core", sum(cpus[::2]), 1), ("single_core_0", cpus[0], 1),
            ("single_core_1", cpus[2], 1), ("performance_restored", mask, threads)]


def experiment(backend, affinity, args, settings):
    cases, rows = inputs(backend), []
    for name, mask, threads in settings:
        affinity.set(mask)
        backend.torch.set_num_threads(threads)
        timed(backend, cases["new"])
        for repeat in range(REPEATS):
            for case, request in cases.items():
                result = timed(backend, request)
                rows.append(dict(block=name, mask=mask, threads=threads, repeat=repeat,
                                 case=case, result=result))
                save(args.out / "calls.json", rows)
        print(json.dumps(dict(block=name, first_action_s=result["first_action_s"])), flush=True)
        save(args.out / f"gpu_{name}.json", dict(state=gpu_state()))


def run(args):
    affinity = WindowsAffinity()
    original = affinity.get()
    mask = performance_mask(affinity.topology(), original)
    backend = SharedQwenInference(args.package)
    try:
        affinity.set(mask)
        start = time.perf_counter()
        backend._load()
        threads = backend.torch.get_num_threads()
        versions = [(n, p._version) for n, p in backend.model.named_parameters()]
        save(args.out / "identity.json", dict(load_s=time.perf_counter()-start,
             threads=threads, original_mask=original, performance_mask=mask, gpu=gpu_state()))
        experiment(backend, affinity, args, blocks(mask, threads))
        save(args.out / "verification.json", dict(
             frozen=all(not p.requires_grad for p in backend.model.parameters()),
             versions_unchanged=versions == [(n, p._version)
                                            for n, p in backend.model.named_parameters()]))
        backend.torch.set_num_threads(threads)
    finally:
        affinity.set(original)
        backend.close()
    save(args.out / "complete.json", dict(restored_mask=affinity.get()))


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
