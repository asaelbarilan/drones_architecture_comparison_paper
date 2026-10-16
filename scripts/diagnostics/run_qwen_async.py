"""One-time bounded D135 local simulator integration test; no training or cloud."""

import argparse
import asyncio
import json
import multiprocessing as mp
import os
import threading
from pathlib import Path

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")

from uavlab.live_qwen.runner import run_suite


def deadline_exit():
    for child in mp.active_children():
        child.terminate()
        child.join(timeout=2)
    os._exit(124)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    settings = json.loads(args.config.read_text())
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "config.json").write_text(json.dumps(settings, indent=2), encoding="utf-8")
    timer = threading.Timer(settings["watchdog_s"], deadline_exit)
    timer.daemon = True
    timer.start()
    try:
        results = asyncio.run(run_suite(settings, args.out))
        (args.out / "result.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(json.dumps(results, indent=2), flush=True)
    finally:
        timer.cancel()


if __name__ == "__main__":
    main()
