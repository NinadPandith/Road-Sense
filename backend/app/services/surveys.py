"""B10: survey jobs (video + GPX) processed by a worker loop polling the surveys table.

States: queued -> extracting -> detecting -> scoring -> merging -> done (or failed).
Frames are sampled at 4 per second. The same pothole seen in consecutive frames is kept once
(the frame with the highest confidence), like Drive mode, so one ride doesn't inflate the
report count. Only frames with a detection are stored (Backend Schema, storage rules).
"""

import logging
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Survey
from app.models.enums import ReportSource, SurveyStatus
from app.services import geo, images, privacy
from app.services.detect import Detection
from app.services.gpx import Track, parse_gpx
from app.services.pipeline import ReportInput, Services, process_frame
from app.services.settings import load_active
from app.services.storage import SURVEY_UPLOADS
from app.services.video import mp4_creation_time, sample_frames, video_info

log = logging.getLogger(__name__)

FRAMES_PER_SECOND = 4
SAME_DEFECT_SECONDS = 2.0  # App Flow, Drive mode: keep one frame per defect within 2 s
POLL_SECONDS = 5
STALE_AFTER = timedelta(minutes=20)

SessionFactory = Callable[[], AbstractContextManager[Session]]


class SurveyError(Exception):
    """A failure with a reason the engineer can act on (shown on the red job card)."""


@dataclass
class Candidate:
    t: float
    lat: float
    lon: float
    rgb: np.ndarray
    dets: list[Detection]

    @property
    def confidence(self) -> float:
        return max(d.confidence for d in self.dets)


@dataclass
class Cluster:
    """Consecutive detections of what is probably the same defect."""

    first: Candidate
    best: Candidate
    last_t: float

    def accepts(self, c: Candidate, radius_m: float) -> bool:
        close = geo.haversine_m(self.first.lat, self.first.lon, c.lat, c.lon) <= radius_m
        return close and c.t - self.last_t <= SAME_DEFECT_SECONDS

    def add(self, c: Candidate) -> None:
        self.last_t = c.t
        if c.confidence > self.best.confidence:
            self.best = c


@dataclass
class Counts:
    detections: int = 0
    new_ids: set[uuid.UUID] = field(default_factory=set)
    merged_ids: set[uuid.UUID] = field(default_factory=set)


def _update(session_factory: SessionFactory, survey_id: uuid.UUID, **values) -> None:
    with session_factory() as db:
        s = db.get(Survey, survey_id)
        if s is not None:
            for k, v in values.items():
                setattr(s, k, v)


def claim_next(db: Session) -> uuid.UUID | None:
    """Take the oldest queued job; SKIP LOCKED makes it safe with more than one worker."""
    return db.execute(
        text(
            """
            update surveys set status = 'extracting', started_at = now(), progress = 0
            where id = (
              select id from surveys where status = 'queued'
              order by created_at limit 1 for update skip locked)
            returning id
            """
        )
    ).scalar()


def requeue_stale(db: Session) -> int:
    """Jobs stuck mid-way (e.g. the container restarted) go back to the queue."""
    return db.execute(
        text(
            "update surveys set status = 'queued', progress = 0 "
            "where status in ('extracting', 'detecting', 'scoring', 'merging') "
            "and updated_at < now() - make_interval(secs => :s)"
        ),
        {"s": STALE_AFTER.total_seconds()},
    ).rowcount


def _video_start(video_bytes: bytes, track: Track | None) -> datetime:
    started = mp4_creation_time(video_bytes)
    if started is None and track is not None and track.start is not None:
        return track.start  # riders usually start the GPS logger and the camera together
    if started is None:
        raise SurveyError("we couldn't read when this video was recorded")
    return started


def run_survey(survey_id: uuid.UUID, session_factory: SessionFactory, services: Services) -> None:
    """Process one claimed job end to end. Never raises: failures end in status 'failed'."""
    with session_factory() as db:
        survey = db.get(Survey, survey_id)
        if survey is None:
            return
        video_path, gpx_path = survey.video_path, survey.gpx_path
        settings = load_active(db)
    storage = services.storage
    try:
        with tempfile.TemporaryDirectory() as tmp:
            video_bytes = storage.download(SURVEY_UPLOADS, video_path)
            vfile = Path(tmp) / "video.mp4"
            vfile.write_bytes(video_bytes)
            track = (
                parse_gpx(storage.download(SURVEY_UPLOADS, gpx_path).decode()) if gpx_path else None
            )
            if track is None or not track.times:
                raise SurveyError("the GPS track has no timed points")
            start = _video_start(video_bytes, track)
            del video_bytes
            info = video_info(vfile)
            if not track.overlaps(start, start + timedelta(seconds=info.duration_s)):
                raise SurveyError("the GPS track doesn't cover this video's time")

            frames_total = max(1, int(info.duration_s * FRAMES_PER_SECOND))
            _update(
                session_factory, survey_id, status=SurveyStatus.detecting, frames_total=frames_total
            )

            # Pass 1: detect on every sampled frame; keep the best frame per defect.
            detector = services.get_detector()
            kept: list[Candidate] = []
            cluster: Cluster | None = None
            for i, (t, rgb) in enumerate(sample_frames(vfile, FRAMES_PER_SECOND)):
                if i % 20 == 0:
                    pct = min(70, int(70 * i / frames_total))
                    _update(session_factory, survey_id, progress=pct)
                dets = detector.detect(rgb, settings.min_confidence)
                pos = track.at(start + timedelta(seconds=t)) if dets else None
                if not dets or pos is None:
                    continue
                c = Candidate(t, pos[0], pos[1], images.resize_max(rgb, images.MAX_SIDE), dets)
                if cluster and cluster.accepts(c, settings.merge_radius_m):
                    cluster.add(c)
                else:
                    if cluster:
                        kept.append(cluster.best)
                    cluster = Cluster(first=c, best=c, last_t=t)
            if cluster:
                kept.append(cluster.best)

            # Pass 2: blur, score, store and merge each kept frame.
            _update(session_factory, survey_id, status=SurveyStatus.scoring, progress=70)
            counts = Counts()
            for j, c in enumerate(kept):
                if not geo.in_pilot_area(c.lat, c.lon):
                    continue
                with session_factory() as db:
                    blurred, _ = privacy.anonymise(c.rgb)
                    result = process_frame(
                        db,
                        services,
                        settings,
                        blurred,
                        ReportInput(
                            lat=c.lat,
                            lon=c.lon,
                            captured_at=start + timedelta(seconds=c.t),
                            source=ReportSource.survey,
                            survey_id=survey_id,
                        ),
                        dets=c.dets,
                    )
                counts.detections += 1
                if result.defect_id:
                    if result.outcome == "new":
                        counts.new_ids.add(result.defect_id)
                    elif result.defect_id not in counts.new_ids:
                        counts.merged_ids.add(result.defect_id)
                if kept:
                    _update(session_factory, survey_id, progress=70 + int(25 * (j + 1) / len(kept)))

            _update(session_factory, survey_id, status=SurveyStatus.merging, progress=97)
        _update(
            session_factory,
            survey_id,
            status=SurveyStatus.done,
            progress=100,
            detections_count=counts.detections,
            defects_new=len(counts.new_ids),
            defects_merged=len(counts.merged_ids),
            finished_at=datetime.now(UTC),
        )
    except Exception as exc:  # noqa: BLE001 - every failure must end the job visibly
        reason = (
            str(exc) if isinstance(exc, SurveyError) else "something went wrong while processing"
        )
        if not isinstance(exc, SurveyError):
            log.exception("Survey %s failed", survey_id)
        _update(
            session_factory,
            survey_id,
            status=SurveyStatus.failed,
            error=reason,
            finished_at=datetime.now(UTC),
        )
    finally:
        # Retention: survey uploads are deleted as soon as the job is done or failed.
        try:
            storage.delete(SURVEY_UPLOADS, [p for p in (video_path, gpx_path) if p])
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not delete survey uploads: %s", exc)


@contextmanager
def committing(factory: Callable[[], Session]) -> Iterator[Session]:
    db = factory()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class SurveyWorker:
    """Background thread in the API process; enough for a few videos a week (Tech Stack)."""

    def __init__(self, session_factory: SessionFactory, services: Services) -> None:
        self.session_factory = session_factory
        self.services = services
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="survey-worker", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def run_once(self) -> bool:
        with self.session_factory() as db:
            requeue_stale(db)
            job = claim_next(db)
        if job is None:
            return False
        log.info("Processing survey %s", job)
        run_survey(job, self.session_factory, self.services)
        return True

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if not self.run_once():
                    self._stop.wait(POLL_SECONDS)
            except Exception:  # noqa: BLE001 - keep the loop alive
                log.exception("Survey worker error")
                time.sleep(POLL_SECONDS)
