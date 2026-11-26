"""Survey videos: when the recording started, and sampling frames at a fixed rate."""

import struct
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import cv2
import numpy as np

MP4_EPOCH = datetime(1904, 1, 1, tzinfo=UTC)
CONTAINERS = {b"moov", b"trak", b"mdia"}


def _boxes(data: bytes, start: int, end: int) -> Iterator[tuple[bytes, int, int]]:
    """Yield (type, payload_start, box_end) for ISO-BMFF boxes in data[start:end]."""
    pos = start
    while pos + 8 <= end:
        size, kind = struct.unpack(">I4s", data[pos : pos + 8])
        header = 8
        if size == 1:
            if pos + 16 > end:
                return
            size = struct.unpack(">Q", data[pos + 8 : pos + 16])[0]
            header = 16
        elif size == 0:
            size = end - pos
        if size < header:
            return
        yield kind, pos + header, min(end, pos + size)
        pos += size


@dataclass(frozen=True)
class Mp4Header:
    created: datetime | None
    duration_s: float | None


def mp4_header(data: bytes) -> Mp4Header | None:
    """Read creation_time and duration from the movie header (mvhd). Phones write UTC."""
    for kind, body, box_end in _boxes(data, 0, len(data)):
        if kind != b"moov":
            continue
        for k2, b2, _ in _boxes(data, body, box_end):
            if k2 != b"mvhd" or b2 + 20 > len(data):
                continue
            if data[b2] == 1:
                secs, _mod, scale, dur = struct.unpack(">QQIQ", data[b2 + 4 : b2 + 32])
            else:
                secs, _mod, scale, dur = struct.unpack(">IIII", data[b2 + 4 : b2 + 20])
            created = MP4_EPOCH + timedelta(seconds=secs) if secs else None
            return Mp4Header(created, dur / scale if scale else None)
    return None


def mp4_creation_time(data: bytes) -> datetime | None:
    h = mp4_header(data)
    return h.created if h else None


def is_mp4(data: bytes) -> bool:
    return len(data) > 12 and data[4:8] == b"ftyp"


@dataclass
class VideoInfo:
    fps: float
    frame_count: int

    @property
    def duration_s(self) -> float:
        return self.frame_count / self.fps if self.fps else 0.0


def video_info(path: Path) -> VideoInfo:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            raise ValueError("unreadable video")
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        return VideoInfo(fps=fps, frame_count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
    finally:
        cap.release()


def sample_frames(path: Path, per_second: float) -> Iterator[tuple[float, np.ndarray]]:
    """Yield (seconds from start, RGB frame) at about `per_second` frames per second."""
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps / per_second))
    idx = 0
    try:
        while cap.grab():
            if idx % step == 0:
                ok, frame = cap.retrieve()
                if not ok:
                    break
                yield idx / fps, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            idx += 1
    finally:
        cap.release()
