"""M13: experiment E6 - is it fast enough?

Measures:
  photo_report   end-to-end POST /reports latency against a running API (local or deployed)
  detector_cpu   YOLO detector frames per second on this machine's CPU (ONNX Runtime)
  depth_cpu      Depth Anything V2 Small frames per second on the CPU
  video          survey-style processing speed (sample + detect) in video frames per second
Browser FPS comes from Drive mode itself: it shows the measured speed on the ride summary.

Usage (from backend/):
    uv run python -m scripts.benchmark --photo road.jpg --api http://localhost:8000 \
        --video ride.mp4 --label laptop-cpu
Writes ../ml/results/e6_timing.json (appends one entry per --label).
"""

import argparse
import json
import statistics
import time
from pathlib import Path

import httpx
import numpy as np

from app.services.depth import get_depth_estimator
from app.services.detect import get_detector
from app.services.video import sample_frames

RESULTS = Path(__file__).resolve().parents[2] / "ml" / "results" / "e6_timing.json"


def photo_latency(api: str, photo: Path, n: int) -> dict:
    data = photo.read_bytes()
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        r = httpx.post(
            f"{api.rstrip('/')}/reports",
            data={"lat": str(12.9716 + i * 0.001), "lon": "77.5946", "source": "drive"},
            files={"image": (photo.name, data, "image/jpeg")},
            timeout=60,
        )
        times.append(time.perf_counter() - t0)
        r.raise_for_status()
    return {
        "n": n,
        "median_s": statistics.median(times),
        "p90_s": float(np.percentile(times, 90)),
        "max_s": max(times),
    }


def model_fps(fn, rgb: np.ndarray, n: int) -> float:
    fn(rgb)
    t0 = time.perf_counter()
    for _ in range(n):
        fn(rgb)
    return n / (time.perf_counter() - t0)


def video_fps(path: Path, per_second: float = 4) -> dict:
    det = get_detector()
    t0 = time.perf_counter()
    frames, seconds = 0, 0.0
    for t, rgb in sample_frames(path, per_second):
        det.detect(rgb)
        frames += 1
        seconds = t
    took = time.perf_counter() - t0
    return {
        "sampled_frames": frames,
        "video_seconds": round(seconds, 1),
        "processing_seconds": round(took, 1),
        "sampled_fps": frames / took if took else 0,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--label", required=True, help="e.g. laptop-cpu, azure-1vcpu")
    ap.add_argument("--photo", type=Path)
    ap.add_argument("--api")
    ap.add_argument("--video", type=Path)
    ap.add_argument("-n", type=int, default=10)
    a = ap.parse_args()

    entry: dict = {"label": a.label}
    rgb = np.random.default_rng(0).integers(0, 255, (720, 1280, 3), dtype=np.uint8)
    entry["detector_cpu_fps"] = model_fps(lambda x: get_detector().detect(x), rgb, a.n)
    depth = get_depth_estimator()
    if depth:
        entry["depth_cpu_fps"] = model_fps(depth.predict, rgb, max(3, a.n // 3))
    if a.api and a.photo:
        entry["photo_report"] = photo_latency(a.api, a.photo, a.n)
    if a.video:
        entry["video"] = video_fps(a.video)

    data = json.loads(RESULTS.read_text()) if RESULTS.exists() else {"runs": []}
    data["runs"] = [r for r in data["runs"] if r["label"] != a.label] + [entry]
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(data, indent=2))
    print(json.dumps(entry, indent=2))


if __name__ == "__main__":
    main()
