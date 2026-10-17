"""Build review-only video from D148 evidence, never execute inference or flights."""

import hashlib
import json
import math
import subprocess
from pathlib import Path

from demo_canvas import SIZE
from demo_flight_frame import flight
from demo_slides import architecture, intro, outcome
from demo_trace import Trace

ROOT = Path("reports/qwen_event_planner_20261017/real_v1")
OUT = Path("reports/linkedin_demo_20261017")
FPS = 20
INTRO_S = 6
ARCH_S = 9
RESULT_S = 9
FINAL_HOLD_S = 2
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def frames(trace, slides):
    for _ in range(INTRO_S*FPS):
        yield slides[0].image
    for index in range(math.ceil(trace.duration*FPS)+1):
        yield flight(trace, min(index/FPS, trace.duration)).image
    final = flight(trace, trace.duration).image
    for _ in range(FINAL_HOLD_S*FPS):
        yield final
    for canvas, duration in zip(slides[1:], (ARCH_S, RESULT_S), strict=False):
        for _ in range(duration*FPS):
            yield canvas.image


def encode(trace, slides):
    args = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo",
            "-pix_fmt", "rgb24", "-s", f"{SIZE[0]}x{SIZE[1]}", "-r", str(FPS),
            "-i", "pipe:0", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT / "linkedin_demo.mp4")]
    with (OUT / "encode.log").open("w") as log:
        process = subprocess.Popen(args, stdin=subprocess.PIPE, stderr=log,
                                   creationflags=NO_WINDOW)
        try:
            for index, frame in enumerate(frames(trace, slides)):
                process.stdin.write(frame.tobytes())
                if index % (FPS*10) == 0:
                    print(f"Encoded {index/FPS:.0f}s", flush=True)
        finally:
            process.stdin.close()
        if process.wait(timeout=60):
            raise RuntimeError("FFmpeg failed; see encode.log")


def main():
    OUT.mkdir(exist_ok=True, parents=True)
    trace = Trace(ROOT)
    slides = (intro(), architecture(), outcome())
    for name, canvas in zip(("poster", "architecture", "outcome"), slides, strict=False):
        canvas.save(OUT / name)
    for seconds in (0, 8, 24, 45, trace.duration):
        flight(trace, seconds).image.save(OUT / f"review_frame_{seconds:05.1f}.png")
    encode(trace, slides)
    data = dict(source="D148 saved evidence; no new flight", flight_seconds=trace.duration,
                fps=FPS, playback_speed=1, camera="saved model-input keyframes, held",
                inference_commit="9c90c57",
                segments_seconds=[INTRO_S, trace.duration, FINAL_HOLD_S, ARCH_S, RESULT_S])
    data["video_sha256"] = hashlib.sha256((OUT / "linkedin_demo.mp4").read_bytes()).hexdigest()
    (OUT / "media_manifest.json").write_text(json.dumps(data, indent=2)+"\n")


if __name__ == "__main__":
    main()
