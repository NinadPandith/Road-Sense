"""GPS tracks: parse a GPX file and find the position at any moment (linear interpolation)."""

import bisect
from dataclasses import dataclass
from datetime import UTC, datetime

import gpxpy


@dataclass
class Track:
    times: list[datetime]
    lats: list[float]
    lons: list[float]

    @property
    def start(self) -> datetime | None:
        return self.times[0] if self.times else None

    @property
    def end(self) -> datetime | None:
        return self.times[-1] if self.times else None

    def at(self, t: datetime) -> tuple[float, float] | None:
        """Position at time t; None outside the track (the frame is 'unplaced')."""
        if not self.times or t < self.times[0] or t > self.times[-1]:
            return None
        i = bisect.bisect_left(self.times, t)
        if self.times[i] == t or i == 0:
            return self.lats[i], self.lons[i]
        t0, t1 = self.times[i - 1], self.times[i]
        f = (t - t0).total_seconds() / max(1e-9, (t1 - t0).total_seconds())
        return (
            self.lats[i - 1] + f * (self.lats[i] - self.lats[i - 1]),
            self.lons[i - 1] + f * (self.lons[i] - self.lons[i - 1]),
        )

    def overlaps(self, start: datetime, end: datetime) -> bool:
        return bool(self.times) and start <= self.times[-1] and end >= self.times[0]


def parse_gpx(text: str) -> Track:
    gpx = gpxpy.parse(text)
    pts = [p for t in gpx.tracks for s in t.segments for p in s.points if p.time is not None]
    pts.sort(key=lambda p: p.time)
    return Track(
        times=[
            (p.time if p.time.tzinfo else p.time.replace(tzinfo=UTC)).astimezone(UTC) for p in pts
        ],
        lats=[p.latitude for p in pts],
        lons=[p.longitude for p in pts],
    )
