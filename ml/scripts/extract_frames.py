"""M5: extract 1 frame per second from a ride video, drop blurry and near-duplicate frames,
and tag each frame with GPS from a GPX track recorded at the same time.

Usage:
    python -m scripts.extract_frames ride1.mp4 --gpx ride1.gpx --out data/frames/ride1 \
        --start "2026-11-30T07:42:10+05:30"
--start is when the video began (phone videos store it as creation_time; we read it with
OpenCV when available, otherwise pass it). Output: JPEG frames + frames.csv
(file, t_s, time_utc, lat, lon, sharpness, segment).
"""

import argparse
import bisect
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import gpxpy
import numpy as np

MIN_SHARPNESS = 60.0  # variance of the Laplacian on a 640 px grey frame
DUP_HAMMING = 6  # dHash distance below which two consecutive kept frames are near-duplicates
SEGMENT_M = 500  # route segment length used later for the train/val/test split


def sharpness(bgr: np.ndarray) -> float:
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    scale = 640 / max(grey.shape)
    if scale < 1:
        grey = cv2.resize(grey, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    return float(cv2.Laplacian(grey, cv2.CV_64F).var())


def dhash(bgr: np.ndarray, size: int = 8) -> int:
    grey = cv2.resize(cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY), (size + 1, size))
    bits = (grey[:, 1:] > grey[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


@dataclass
class Track:
    times: list[datetime]
    lats: list[float]
    lons: list[float]
    dist: list[float]  # cumulative distance along the track in metres

    def at(self, t: datetime) -> tuple[float, float, float] | None:
        """Linear interpolation of (lat, lon, distance) at time t; None outside the track."""
        if not self.times or t < self.times[0] or t > self.times[-1]:
            return None
        i = bisect.bisect_left(self.times, t)
        if self.times[i] == t or i == 0:
            return self.lats[i], self.lons[i], self.dist[i]
        t0, t1 = self.times[i - 1], self.times[i]
        f = (t - t0).total_seconds() / max(1e-9, (t1 - t0).total_seconds())
        lerp = lambda a: a[i - 1] + f * (a[i] - a[i - 1])  # noqa: E731
        return lerp(self.lats), lerp(self.lons), lerp(self.dist)


def load_gpx(path: Path) -> Track:
    gpx = gpxpy.parse(path.read_text())
    pts = [p for t in gpx.tracks for s in t.segments for p in s.points if p.time]
    pts.sort(key=lambda p: p.time)
    dist, total = [], 0.0
    for i, p in enumerate(pts):
        if i:
            total += p.distance_2d(pts[i - 1]) or 0.0
        dist.append(total)
    return Track(
        times=[p.time.astimezone(timezone.utc) for p in pts],
        lats=[p.latitude for p in pts],
        lons=[p.longitude for p in pts],
        dist=dist,
    )


def extract(
    video: Path,
    out: Path,
    track: Track | None,
    start: datetime | None,
    fps_out: float = 1.0,
) -> list[dict]:
    cap = cv2.VideoCapture(str(video))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / fps_out))
    out.mkdir(parents=True, exist_ok=True)
    rows, last_hash, idx = [], None, 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if idx % step == 0:
            ok, frame = cap.retrieve()
            if not ok:
                break
            t_s = idx / fps
            sharp = sharpness(frame)
            h = dhash(frame)
            if sharp >= MIN_SHARPNESS and (
                last_hash is None or hamming(h, last_hash) > DUP_HAMMING
            ):
                last_hash = h
                name = f"{video.stem}_{int(t_s * 1000):08d}.jpg"
                cv2.imwrite(str(out / name), frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
                row = {
                    "file": name,
                    "t_s": round(t_s, 2),
                    "time_utc": "",
                    "lat": "",
                    "lon": "",
                    "sharpness": round(sharp, 1),
                    "segment": "",
                }
                if start is not None:
                    t = start + timedelta(seconds=t_s)
                    row["time_utc"] = t.isoformat()
                    pos = track.at(t) if track else None
                    if pos:
                        row["lat"], row["lon"] = round(pos[0], 7), round(pos[1], 7)
                        row["segment"] = int(pos[2] // SEGMENT_M)
                rows.append(row)
        idx += 1
    cap.release()
    with (out / "frames.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["file"])
        w.writeheader()
        w.writerows(rows)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("video", type=Path)
    ap.add_argument("--gpx", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--start", help="video start time, ISO 8601 with timezone")
    ap.add_argument("--fps", type=float, default=1.0)
    a = ap.parse_args()
    start = datetime.fromisoformat(a.start).astimezone(timezone.utc) if a.start else None
    track = load_gpx(a.gpx) if a.gpx else None
    rows = extract(a.video, a.out, track, start, a.fps)
    placed = sum(1 for r in rows if r["lat"] != "")
    print(f"kept {len(rows)} frames ({placed} with GPS) -> {a.out}")


if __name__ == "__main__":
    main()
