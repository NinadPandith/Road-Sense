"""B9: staff endpoints, auth, demo role and status rules."""

import csv
import io
import time
import uuid

import jwt
import pytest
from sqlalchemy import select, text

from app.api.deps import get_services
from app.core.config import get_settings
from app.models import Defect, SettingsVersion
from tests.fakes import LAT, LON, fake_services, metres_north, road_photo

pytestmark = pytest.mark.db
SECRET = "test-jwt-secret-that-is-long-enough-for-hs256"


@pytest.fixture
def api(app, db_client, tmp_path, monkeypatch):
    monkeypatch.setattr(get_settings(), "supabase_jwt_secret", SECRET)
    monkeypatch.setattr(get_settings(), "cron_secret", "cron-test")
    app.dependency_overrides[get_services] = lambda: fake_services(tmp_path)
    return db_client


def make_user(db, role: str) -> dict:
    uid = uuid.uuid4()
    db.execute(
        text("insert into auth.users (id, email) values (:id, :e)"), {"id": uid, "e": f"{uid}@x"}
    )
    db.execute(
        text("insert into profiles (id, full_name, role) values (:id, :n, :r)"),
        {"id": uid, "n": f"{role.title()} One", "r": role},
    )
    token = jwt.encode(
        {"sub": str(uid), "aud": "authenticated", "exp": int(time.time()) + 3600},
        SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def engineer(db):
    return make_user(db, "engineer")


@pytest.fixture
def demo(db):
    return make_user(db, "demo")


def report(api, metres=0.0, seed=0):
    r = api.post(
        "/reports",
        data={"lat": str(metres_north(LAT, metres)), "lon": str(LON)},
        files={"image": ("p.jpg", road_photo(seed), "image/jpeg")},
        headers={"x-forwarded-for": f"9.9.9.{seed}"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_staff_routes_need_a_valid_token(api):
    assert api.get("/defects").status_code == 401
    r = api.get("/defects", headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 401 and r.json()["error"]["code"] == "unauthorized"


def test_token_without_profile_is_rejected(api):
    token = jwt.encode({"sub": str(uuid.uuid4()), "aud": "authenticated"}, SECRET, "HS256")
    assert api.get("/defects", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_list_defects_ranked_by_priority(api, engineer, db):
    report(api, 0, 0)
    report(api, 50, 1)
    report(api, 51, 2)  # merges with the second: higher n -> higher priority
    r = api.get("/defects", headers=engineer)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert [i["rank"] for i in body["items"]] == [1, 2]
    assert body["items"][0]["report_count"] == 2
    assert "2 reports" in body["items"][0]["priority_reason"]
    assert body["items"][0]["thumb_url"].startswith("http://test/local-storage/report-images/")


def test_list_filters_and_bbox(api, engineer):
    report(api, 0, 0)
    report(api, 500, 1)
    near = f"{LON - 0.001},{LAT - 0.001},{LON + 0.001},{LAT + 0.001}"
    assert api.get(f"/defects?bbox={near}", headers=engineer).json()["total"] == 1
    assert (
        api.get(
            "/defects?severity=minor&severity=moderate&severity=dangerous", headers=engineer
        ).json()["total"]
        == 2
    )
    assert api.get("/defects?status=fixed", headers=engineer).json()["total"] == 0
    assert api.get("/defects?road_class=residential", headers=engineer).json()["total"] == 0


def test_defect_detail_explains_severity_and_priority(api, engineer):
    did = report(api)["defect_id"]
    r = api.get(f"/defects/{did}", headers=engineer)
    assert r.status_code == 200
    d = r.json()
    assert set(d["priority_terms"]) == {"S", "R", "n", "t", "B"}
    assert len(d["reports"]) == 1 and d["reports"][0]["detections"][0]["size_score"] >= 0
    assert d["history"][0]["to_status"] == "reported"
    assert d["merge_radius_m"] == 5


def test_status_change_and_history(api, engineer, db):
    did = report(api)["defect_id"]
    for to in ("verified", "assigned", "fixed"):
        r = api.patch(f"/defects/{did}/status", data={"to_status": to}, headers=engineer)
        assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "fixed" and d["fixed_at"]
    assert [h["to_status"] for h in d["history"]] == ["fixed", "assigned", "verified", "reported"]
    assert d["history"][0]["changed_by"] == "Engineer One"


@pytest.mark.parametrize(
    ("start", "to"),
    [
        ("reported", "fixed"),
        ("fixed", "reported"),
        ("rejected", "reported"),
        ("needs_review", "assigned"),
        ("verified", "reported"),
    ],
)
def test_disallowed_transitions(api, engineer, db, start, to):
    did = report(api)["defect_id"]
    db.execute(text("update defects set status = :s where id = :id"), {"s": start, "id": did})
    r = api.patch(f"/defects/{did}/status", data={"to_status": to}, headers=engineer)
    assert r.status_code == 409 and r.json()["error"]["code"] == "invalid_transition"


def test_fixed_photo_is_stored_and_shown_on_tracking_page(api, engineer, tmp_path):
    res = report(api)
    did, code = res["defect_id"], res["tracking_code"]
    api.patch(f"/defects/{did}/status", data={"to_status": "assigned"}, headers=engineer)
    r = api.patch(
        f"/defects/{did}/status",
        data={"to_status": "fixed"},
        files={"fixed_photo": ("after.jpg", road_photo(7), "image/jpeg")},
        headers=engineer,
    )
    assert r.json()["fixed_photo_url"]
    t = api.get(f"/track/{code}").json()
    assert t["defect_status"] == "fixed" and t["fixed_photo_url"]
    assert all(step["at"] for step in t["timeline"][:1]) and t["timeline"][3]["at"]


def test_demo_user_can_read_but_not_write(api, demo):
    did = report(api)["defect_id"]
    assert api.get("/defects", headers=demo).status_code == 200
    assert api.get(f"/defects/{did}", headers=demo).status_code == 200
    r = api.patch(f"/defects/{did}/status", data={"to_status": "verified"}, headers=demo)
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden_demo"
    assert (
        api.post(
            "/defects/bulk-status", json={"ids": [did], "to_status": "verified"}, headers=demo
        ).status_code
        == 403
    )
    assert api.post("/settings", json={}, headers=demo).status_code == 403


def test_bulk_status_skips_invalid(api, engineer, db):
    a = report(api, 0, 0)["defect_id"]
    b = report(api, 100, 1)["defect_id"]
    db.execute(text("update defects set status = 'rejected' where id = :id"), {"id": b})
    r = api.post(
        "/defects/bulk-status", json={"ids": [a, b], "to_status": "assigned"}, headers=engineer
    )
    assert r.json() == {"updated": 1, "skipped": [b]}


def test_repair_list_csv(api, engineer):
    report(api)
    r = api.get("/repair-list.csv", headers=engineer)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows) == 1 and rows[0]["rank"] == "1" and rows[0]["damage_type"] == "pothole"


def test_stats(api, engineer):
    report(api)
    s = api.get("/stats", headers=engineer).json()
    assert s["open_defects"] == 1 and s["new_this_week"] == 1
    assert sum(w["reported"] for w in s["per_week"]) == 1


def test_settings_change_is_versioned_and_recalculates(api, engineer, db):
    did = report(api)["defect_id"]
    before = db.get(Defect, uuid.UUID(did)).priority
    body = api.get("/settings", headers=engineer).json()
    body["road_weights"]["major"] = 0.5
    r = api.post("/settings", json=body, headers=engineer)
    assert r.status_code == 200
    assert (
        db.scalar(select(SettingsVersion).order_by(SettingsVersion.id.desc())).values[
            "road_weights"
        ]["major"]
        == 0.5
    )
    db.expire_all()
    assert db.get(Defect, uuid.UUID(did)).priority == pytest.approx(before / 2, rel=1e-3)
    history = api.get("/settings/history", headers=engineer).json()
    assert history[0]["created_by"] == "Engineer One"
    assert history[0]["values"]["road_weights"]["major"] == 0.5


def test_nightly_recalculate_needs_cron_secret(api):
    report(api)
    assert api.post("/admin/recalculate").status_code == 401
    r = api.post("/admin/recalculate", headers={"x-cron-secret": "cron-test"})
    assert r.status_code == 200 and r.json() == {"updated": 1}


def test_me(api, engineer):
    assert api.get("/me", headers=engineer).json()["role"] == "engineer"


def test_accepting_needs_review_uses_engineer_severity(api, engineer, db, tmp_path):
    from app.api.deps import get_services
    from tests.fakes import FakeDetector, fake_services

    det = FakeDetector()
    det.next = []
    api.app.dependency_overrides[get_services] = lambda: fake_services(tmp_path, det)
    code = report(api)["tracking_code"]
    did = api.post(f"/reports/{code}/send-anyway").json()["defect_id"]
    r = api.patch(
        f"/defects/{did}/status",
        data={"to_status": "reported", "damage_class": "pothole", "severity_label": "dangerous"},
        headers=engineer,
    )
    body = r.json()
    assert body["status"] == "reported" and body["damage_class"] == "pothole"
    assert body["severity_label"] == "dangerous" and body["priority"] > 0


def test_not_a_defect_rejects_and_leaves_the_list(api, engineer):
    did = report(api)["defect_id"]
    r = api.patch(
        f"/defects/{did}/status",
        data={"to_status": "rejected", "reason": "speed breaker"},
        headers=engineer,
    )
    assert r.json()["status"] == "rejected"
    assert api.get("/defects", headers=engineer).json()["total"] == 0
    assert api.get("/defects?status=rejected", headers=engineer).json()["total"] == 1
