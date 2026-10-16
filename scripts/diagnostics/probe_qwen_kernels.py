"""Bounded D138 saved-input kernel/cache A/B; never executes actions."""

import argparse
import importlib.util
import json
import os
import threading
import time
import warnings
from collections import Counter
from contextlib import contextmanager, nullcontext
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from probe_qwen_regression import inputs
from probe_qwen_stream import measure, requests, save

from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.shared_qwen import SharedQwenInference

WATCHDOG_SECONDS = 1200
TIMED_REPEATS = 25


def cases_for(backend):
    config = json.loads(Path("reports/qwen_stream_20261016/real_v2/config.json").read_text())
    image = Path("reports/shared_qwen_vla_20261016/final/input.png")
    cases = requests(config, image, backend.model_id)
    cases.append(inputs(backend)["new"])
    return cases


@contextmanager
def variant(backend, name):
    from torch.nn.attention import SDPBackend, sdpa_kernel

    config = backend.model.generation_config
    previous = config.cache_implementation
    context = nullcontext()
    if name == "flash":
        context = sdpa_kernel(SDPBackend.FLASH_ATTENTION)
    elif name in {"efficient", "expanded"}:
        context = sdpa_kernel(SDPBackend.EFFICIENT_ATTENTION)
    elif name == "static":
        config.cache_implementation = "static"
    try:
        with context, expanded_heads(backend, name == "expanded"):
            yield
    finally:
        config.cache_implementation = previous


@contextmanager
def expanded_heads(backend, enabled):
    functional = backend.torch.nn.functional
    original = functional.scaled_dot_product_attention

    def expanded(*args, **kwargs):
        query, key, value, *rest = args
        if kwargs.pop("enable_gqa", False):
            groups = query.shape[-3] // key.shape[-3]
            key = key.repeat_interleave(groups, dim=-3)
            value = value.repeat_interleave(groups, dim=-3)
        return original(query, key, value, *rest, **kwargs)

    if enabled:
        functional.scaled_dot_product_attention = expanded
    try:
        yield
    finally:
        functional.scaled_dot_product_attention = original


def attention_audit(backend, request):
    functional = backend.torch.nn.functional
    original = functional.scaled_dot_product_attention
    shapes = Counter()

    def observe(*args, **kwargs):
        tensors = args[:3]
        key = json.dumps([dict(shape=list(t.shape), dtype=str(t.dtype),
                               stride=list(t.stride())) for t in tensors])
        shapes[key] += 1
        return original(*args, **kwargs)

    functional.scaled_dot_product_attention = observe
    try:
        result = measure(backend, request, "first_action")
    finally:
        functional.scaled_dot_product_attention = original
    return dict(result=result, calls=[dict(tensors=json.loads(k), count=v)
                                     for k, v in shapes.items()])


def attempt(backend, request, name):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            with variant(backend, name):
                result = measure(backend, request, "first_action")
            return dict(ok=True, result=result, warnings=[str(w.message) for w in caught])
        except Exception as error:
            return dict(ok=False, error=repr(error), warnings=[str(w.message) for w in caught])


def compile_probe(torch):
    """Check installed compiler availability without downloading or changing packages."""
    start = time.perf_counter()
    if importlib.util.find_spec("triton") is None:
        return dict(ok=False, error="No installed Triton; no stack changes authorized.",
                    prior_attempt="Tiny torch.compile probe stalled and was interrupted.")
    try:
        sample = torch.ones(64, device="cuda")
        compiled = torch.compile(lambda x: x.sin() + x, fullgraph=True)
        with torch.inference_mode():
            output = compiled(sample)
        torch.cuda.synchronize()
        return dict(ok=True, seconds=time.perf_counter()-start,
                    equal=torch.equal(output, sample.sin()+sample))
    except Exception as error:
        return dict(ok=False, seconds=time.perf_counter()-start, error=repr(error))


def paired(backend, cases, names, out):
    rows = []
    for repeat in range(TIMED_REPEATS):
        for index, request in enumerate(cases):
            order = names[repeat % len(names):] + names[:repeat % len(names)]
            results = {name: attempt(backend, request, name) for name in order}
            reference = results["baseline"]
            equal = {name: value["ok"] and reference["ok"] and
                     value["result"]["tokens"] == reference["result"]["tokens"] and
                     value["result"]["actions"] == reference["result"]["actions"]
                     for name, value in results.items()}
            rows.append(dict(repeat=repeat, case=index, results=results, equal=equal))
            save(out / "pairs.json", rows)
        print(json.dumps(dict(repeat=repeat, pairs=len(rows), equal=equal)), flush=True)
    return rows


def role_checks(backend, cases, names):
    rows = []
    for role in ("planner", "direction", "monitor"):
        request = InferenceRequest(model_id=backend.model_id, role=role, prompt_hash="d138",
                                   prompt="Reply with exactly one word: ready.")
        baseline, _ = backend._run(request)
        for name in names:
            with variant(backend, name):
                response, _ = backend._run(request)
                pilot = measure(backend, cases[0], "first_action")
            rows.append(dict(role=role, variant=name, response=response,
                             equals_baseline=response == baseline, pilot=pilot))
    return rows


def run(args):
    backend = SharedQwenInference(args.package, max_new_tokens=8)
    try:
        backend._load()
        versions = [(n, p._version) for n, p in backend.model.named_parameters()]
        cases = cases_for(backend)
        save(args.out / "inputs.json", [dict(prompt=r.prompt, images=r.images) for r in cases])
        save(args.out / "attention.json", attention_audit(backend, cases[0]))
        checks = {name: attempt(backend, cases[0], name)
                  for name in ("baseline", "flash", "efficient", "expanded", "static")}
        save(args.out / "eligibility.json", checks)
        save(args.out / "compiler.json", compile_probe(backend.torch))
        names = [name for name, check in checks.items() if check["ok"]]
        paired(backend, cases, names, args.out)
        save(args.out / "roles.json", role_checks(backend, cases, names))
        save(args.out / "complete.json", dict(
            names=names, loads=backend.load_count,
            versions_unchanged=versions == [(n, p._version)
                                           for n, p in backend.model.named_parameters()],
            frozen=all(not p.requires_grad for p in backend.model.parameters()),
            devices=dict(Counter(str(p.device) for p in backend.model.parameters())),
            peak_bytes=backend.torch.cuda.max_memory_allocated(),
            torch=backend.torch.__version__,
            transformers=__import__("transformers").__version__))
    finally:
        backend.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True)
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
