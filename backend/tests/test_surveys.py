"""B10: survey upload, worker states, GPX matching and per-defect de-duplication."""

from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

import cv2
import numpy as np
import pytest
from sqlalchemy import select

from app.api.deps import get_services
from app.models import Defect, Report, Survey
from app.models.enums import DamageClass, SurveyStatus
from app.services.detect import Detection
from app.services.surveys import SurveyWorker
from app.services.video import is_mp4, mp4_header
from tests.fakes import LAT, LON, fake_services
from tests.test_staff_api import make_user

pytestmark = pytest.mark.db

START = datetime(2026, 11, 30, 2, 0, 0, tzinfo=UTC)
# Seconds where the fake detector sees damage. At 1.1 m/s: window 1 at ~2 m, window 2 at ~7 m
# (within 5 m of window 1's defect -> merged into it), window 3 at ~10 m and 2.5 s later (a new
# cluster, more than 5 m from the averaged defect -> a second defect).
BRIGHT = [(2.0, 3.0), (6.0, 7.0), (9.5, 9.8)]


def make_video(path, seconds=10, fps=10):
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    rng = np.random.default_rng(0)
    for i in range(seconds * fps):
        t = i / fps
        base = 200 if any(a <= t <= b for a, b in BRIGHT) else 80
        vw.write(np.clip(base + rng.integers(-30, 30, (240, 320, 3)), 0, 255).astype(np.uint8))
    vw.release()
    return path.read_bytes()


def make_gpx(seconds=12, metres_per_s=1.1):
    pts = "".join(
        f'<trkpt lat="{LAT + i * metres_per_s / 111_320}" lon="{LON}"><time>'
        f"{(START + timedelta(seconds=i)).strftime('%Y-%m-%dT%H:%M:%SZ')}</time></trkpt>"
        for i in range(seconds)
    )
    return (
        '<?xml version="1.0"?><gpx version="1.1" creator="t" '
        f'xmlns="http://www.topografix.com/GPX/1/1"><trk><trkseg>{pts}</trkseg></trk></gpx>'
    ).encode()


class BrightnessDetector:
    def detect(self, rgb, conf_threshold=0.35):
        if rgb.mean() > 150:
            return [Detection(DamageClass.pothole, 0.8, (0.3, 0.55, 0.7, 0.95))]
        return []


@pytest.fixture
def setup(app, db_client, db, tmp_path, monkeypatch):
    from app.core.config import get_settings
    from tests.test_staff_api import SECRET

    monkeypatch.setattr(get_settings(), "supabase_jwt_secret", SECRET)
    services = fake_services(tmp_path)
    services.get_detector = lambda: BrightnessDetector()
    app.dependency_overrides[get_services] = lambda: services

    @contextmanager
    def factory():
        yield db
        db.flush()

    worker = SurveyWorker(factory, services)
    return db_client, make_user(db, "engineer"), worker, tmp_path


def upload(api, headers, tmp_path, name="Ride 1"):
    video = make_video(tmp_path / "ride.mp4")
    return api.post(
        "/surveys",
        data={"name": name},
        files={
            "video": ("ride.mp4", video, "video/mp4"),
            "gpx": ("ride.gpx", make_gpx(), "application/gpx+xml"),
        },
        headers=headers,
    )


def test_mp4_header_is_read(tmp_path):
    data = make_video(tmp_path / "v.mp4", seconds=2)
    assert is_mp4(data)
    h = mp4_header(data)
    assert h is not None and h.duration_s == pytest.approx(2.0, abs=0.2)


def test_survey_becomes_defects_with_locations(setup, db):
    api, eng, worker, tmp_path = setup
    r = upload(api, eng, tmp_path)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "queued"
    assert worker.run_once() is True

    s = db.scalar(select(Survey))
    assert s.status == SurveyStatus.done and s.progress == 100, s.error
    assert (s.detections_count, s.defects_new, s.defects_merged) == (3, 2, 0)
    reports = db.scalars(select(Report).order_by(Report.captured_at)).all()
    assert [r.source.value for r in reports] == ["survey"] * 3
    assert reports[0].captured_at >= START + timedelta(seconds=2)
    assert all(r.image_path for r in reports)  # only frames with damage are stored
    assert not list((tmp_path / "survey-uploads").rglob("*.mp4"))  # uploads deleted
    assert worker.run_once() is False  # queue empty

    # Riding the same route again adds to the same defects.
    upload(api, eng, tmp_path, "Ride 2")
    worker.run_once()
    s2 = db.scalar(select(Survey).where(Survey.name == "Ride 2"))
    assert (s2.defects_new, s2.defects_merged) == (0, 2)
    assert len(db.scalars(select(Defect)).all()) == 2

    listed = api.get("/surveys", headers=eng).json()
    assert len(listed) == 2
    filtered = api.get(f"/defects?survey_id={s.id}", headers=eng).json()
    assert filtered["total"] == 2


def test_gpx_outside_video_time_warns_and_fails_with_reason(setup, db, monkeypatch):
    from app.api import surveys as survey_api
    from app.services import surveys as survey_service
    from app.services.video import Mp4Header

    api, eng, worker, tmp_path = setup
    later = START + timedelta(hours=7)
    monkeypatch.setattr(survey_api, "mp4_header", lambda _: Mp4Header(later, 10.0))
    monkeypatch.setattr(survey_service, "mp4_creation_time", lambda _: later)
    r = upload(api, eng, tmp_path)
    assert r.json()["gpx_overlap"] is False  # the screen warns before processing
    worker.run_once()
    s = db.scalar(select(Survey))
    assert s.status == SurveyStatus.failed
    assert s.error == "the GPS track doesn't cover this video's time"
    assert not list((tmp_path / "survey-uploads").rglob("*.*"))


def test_non_mp4_is_rejected(setup):
    api, eng, _, _ = setup
    r = api.post(
        "/surveys",
        data={"name": "x"},
        files={"video": ("a.mp4", b"not a video", "video/mp4"), "gpx": ("a.gpx", make_gpx(), "x")},
        headers=eng,
    )
    assert r.status_code == 415


def test_bad_gpx_is_rejected(setup, tmp_path):
    api, eng, _, _ = setup
    r = api.post(
        "/surveys",
        data={"name": "x"},
        files={
            "video": ("a.mp4", make_video(tmp_path / "a.mp4", 1), "video/mp4"),
            "gpx": ("a.gpx", b"<gpx></gpx>", "x"),
        },
        headers=eng,
    )
    assert r.status_code == 422 and r.json()["error"]["code"] == "survey_gpx_mismatch"


def test_demo_user_cannot_upload(setup, db, tmp_path):
    api, _, _, _ = setup
    demo = make_user(db, "demo")
    assert upload(api, demo, tmp_path).status_code == 403
