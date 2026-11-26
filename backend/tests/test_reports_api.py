"""B5 + B6 + B7: POST /reports end to end against PostGIS, with fake models."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text

from app.api.deps import get_services
from app.models import Defect, Detection, Report, StatusHistory
from app.models.enums import DamageClass, DefectStatus
from app.services.detect import Detection as Det
from tests.fakes import LAT, LON, FakeDetector, fake_services, metres_north, road_photo

pytestmark = pytest.mark.db


@pytest.fixture
def detector():
    return FakeDetector()


@pytest.fixture
def api(app, db_client, tmp_path, detector):
    app.dependency_overrides[get_services] = lambda: fake_services(tmp_path, detector)
    return db_client


def post(api, lat=LAT, lon=LON, seed=0, ip="1.2.3.4", **form):
    data = {"lat": str(lat), "lon": str(lon), **{k: str(v) for k, v in form.items()}}
    return api.post(
        "/reports",
        data=data,
        files={"image": ("photo.jpg", road_photo(seed), "image/jpeg")},
        headers={"x-forwarded-for": ip},
    )


def test_upload_returns_full_result_and_saves_rows(api, db, tmp_path):
    r = post(api)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "new"
    assert body["tracking_code"].startswith("RS-")
    assert body["damage_class"] == "pothole"
    assert body["confidence_label"] == "very_likely"
    assert body["severity"]["label"] in {"moderate", "dangerous"}
    assert set(body["severity"]["factors"]) == {"size", "depth", "type", "position"}
    assert body["report_count"] == 1

    report = db.scalar(select(Report))
    assert report.model_version == "test-model"
    assert db.scalar(select(Detection)).severity_score == pytest.approx(
        body["severity"]["score"], abs=0.01
    )
    defect = db.scalar(select(Defect))
    assert defect.road_class.value == "major" and defect.road_name == "MG Road"
    assert defect.priority > 0 and set(defect.priority_terms) == {"S", "R", "n", "t", "B"}
    assert (tmp_path / "report-images" / report.image_path).exists()
    assert (tmp_path / "report-images" / report.thumb_path).exists()


def test_two_uploads_3m_apart_merge_into_one_defect(api, db):
    post(api)
    r = post(api, lat=metres_north(LAT, 3), seed=1)
    assert r.json()["outcome"] == "merged"
    assert r.json()["report_count"] == 2
    defects = db.scalars(select(Defect)).all()
    assert len(defects) == 1 and defects[0].report_count == 2


def test_uploads_6m_apart_stay_separate(api, db):
    post(api)
    r = post(api, lat=metres_north(LAT, 6), seed=1)
    assert r.json()["outcome"] == "new"
    assert len(db.scalars(select(Defect)).all()) == 2


def test_merge_moves_location_to_average_and_keeps_highest_severity(api, db, detector):
    detector.next = [Det(DamageClass.crack_along, 0.6, (0.0, 0.8, 0.05, 0.85))]
    post(api)
    detector.next = [Det(DamageClass.pothole, 0.9, (0.3, 0.55, 0.7, 0.95))]
    post(api, lat=metres_north(LAT, 4), seed=1)
    defect = db.scalar(select(Defect))
    assert defect.damage_class == DamageClass.pothole
    lat = db.execute(text("select ST_Y(location::geometry) from defects")).scalar()
    assert lat == pytest.approx(metres_north(LAT, 2), abs=1e-6)


def test_third_report_auto_verifies(api, db):
    for i in range(3):
        post(api, lat=metres_north(LAT, i), seed=i)
    defect = db.scalar(select(Defect))
    assert defect.status == DefectStatus.verified
    hist = db.scalars(select(StatusHistory).order_by(StatusHistory.id)).all()
    assert hist[-1].to_status == DefectStatus.verified and hist[-1].changed_by is None


def test_report_on_recently_fixed_defect_reopens_it(api, db):
    post(api)
    defect = db.scalar(select(Defect))
    defect.status = DefectStatus.fixed
    defect.fixed_at = datetime.now(UTC) - timedelta(days=5)
    db.flush()
    r = post(api, seed=1)
    assert r.json()["outcome"] == "merged"
    db.refresh(defect)
    assert defect.status == DefectStatus.reported and defect.reopened_count == 1


def test_report_on_long_fixed_defect_creates_new_one(api, db):
    post(api)
    defect = db.scalar(select(Defect))
    defect.status = DefectStatus.fixed
    defect.fixed_at = datetime.now(UTC) - timedelta(days=40)
    db.flush()
    assert post(api, seed=1).json()["outcome"] == "new"


def test_no_damage_then_send_anyway_goes_to_needs_review(api, db, detector):
    detector.next = []
    r = post(api)
    assert r.json()["outcome"] == "no_damage"
    assert db.scalar(select(Defect)) is None
    code = r.json()["tracking_code"]
    r2 = api.post(f"/reports/{code}/send-anyway")
    assert r2.json()["outcome"] == "needs_review"
    defect = db.scalar(select(Defect))
    assert defect.status == DefectStatus.needs_review and defect.damage_class is None


def test_rate_limit_after_10_reports_per_hour(api):
    for i in range(10):
        assert post(api, lat=metres_north(LAT, 10 * i), seed=i).status_code == 200
    r = post(api, seed=99)
    assert r.status_code == 429
    assert r.json()["error"]["code"] == "rate_limited"
    assert post(api, seed=99, ip="5.6.7.8").status_code == 200  # other network still fine
    # Drive mode has its own, higher limit, so a ride isn't blocked by citizen photos.
    assert post(api, lat=metres_north(LAT, 500), seed=98, source="drive").status_code == 200


def test_same_client_report_id_is_idempotent(api, db):
    cid = str(uuid.uuid4())
    a = post(api, client_report_id=cid).json()
    b = post(api, client_report_id=cid, seed=1).json()
    assert a["tracking_code"] == b["tracking_code"]
    assert len(db.scalars(select(Report)).all()) == 1


def test_non_image_upload_is_rejected(api):
    r = api.post(
        "/reports",
        data={"lat": str(LAT), "lon": str(LON)},
        files={"image": ("x.jpg", b"definitely not a jpeg", "image/jpeg")},
    )
    assert r.status_code == 415 and r.json()["error"]["code"] == "invalid_image"


def test_new_defect_gets_ward_and_nearby_school(api, db):
    d = 0.01
    db.execute(
        text(
            "insert into wards (code, name, boundary) values ('W-1', 'Ward 1', "
            f"ST_GeogFromText('MULTIPOLYGON((({LON - d} {LAT - d}, {LON + d} {LAT - d}, "
            f"{LON + d} {LAT + d}, {LON - d} {LAT + d}, {LON - d} {LAT - d})))'))"
        )
    )
    db.execute(
        text(
            "insert into sensitive_places (kind, name, osm_id, location) values "
            "('school', 'Govt School', 1, ST_MakePoint(:lon, :lat)::geography)"
        ),
        {"lon": LON, "lat": metres_north(LAT, 150)},
    )
    post(api)
    defect = db.scalar(select(Defect))
    assert defect.ward_id is not None
    assert defect.near_sensitive and defect.priority_terms["B"] == 1.3


def test_track_shows_status_timeline(api, db):
    code = post(api).json()["tracking_code"]
    r = api.get(f"/track/{code.lower()}")
    assert r.status_code == 200
    body = r.json()
    assert body["defect_status"] == "reported"
    assert [s["status"] for s in body["timeline"]] == ["reported", "verified", "assigned", "fixed"]
    assert body["timeline"][0]["at"] is not None and body["timeline"][1]["at"] is None


def test_unknown_tracking_code_is_not_found(api):
    r = api.get("/track/RS-ZZZZ")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
