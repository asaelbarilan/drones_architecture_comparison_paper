"""One-time D135 saved-input thread-budget comparison, without motion or training."""

import argparse
import base64
import json
import os
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from probe_qwen_stream import measure

from uavlab.interfaces import InferenceRequest
from uavlab.plugins.inference.shared_qwen import SharedQwenInference


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--package", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in (args.source / "events.jsonl").read_text().splitlines()]
    row = next(r for r in rows if r["kind"] == "submitted" and r["role"] == "pilot")
    image = base64.b64encode((args.source / row["image_files"][0]).read_bytes()).decode()
    backend = SharedQwenInference(args.package)
    try:
        backend._load()
        request = InferenceRequest(model_id=backend.model_id, role="pilot", prompt_hash="d135",
                                    prompt=row["prompt"], images=(image,), image_count=1)
        original = backend.torch.get_num_threads()
        results = []
        for threads in (original, 1, 1, 1, original):
            backend.torch.set_num_threads(threads)
            results.append(dict(threads=threads, result=measure(backend, request, "first_action")))
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps([dict(threads=r["threads"], seconds=r["result"]["seconds"],
                               tokens=r["result"]["tokens"]) for r in results]), flush=True)
    finally:
        backend.close()


if __name__ == "__main__":
    main()
