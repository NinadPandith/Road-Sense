"""B1: migrations create the tables, view, policies and constraints from the Backend Schema."""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

pytestmark = pytest.mark.db

TABLES = {
    "profiles",
    "wards",
    "sensitive_places",
    "surveys",
    "defects",
    "reports",
    "detections",
    "status_history",
    "settings_versions",
}


def test_all_tables_exist(db):
    rows = db.execute(text("select tablename from pg_tables where schemaname = 'public'")).scalars()
    assert set(rows) >= TABLES


def test_rls_enabled_on_every_app_table(db):
    rows = db.execute(
        text(
            "select relname from pg_class "
            "where relrowsecurity and relnamespace = 'public'::regnamespace"
        )
    ).scalars()
    assert set(rows) >= TABLES


def test_public_defects_view_hides_rejected(db):
    db.execute(
        text(
            "insert into defects (location, status) values "
            "(ST_MakePoint(77.59, 12.97)::geography, 'reported'),"
            "(ST_MakePoint(77.60, 12.97)::geography, 'rejected')"
        )
    )
    statuses = set(db.execute(text("select status::text from public_defects")).scalars())
    assert statuses == {"reported"}


@pytest.mark.parametrize("code", ["RS-0OIL", "rs-7K2Q", "RS-7K", "RS-7K2Q99X"])
def test_tracking_code_check_rejects_bad_codes(db, code):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            text(
                "insert into reports (tracking_code, source, location, captured_at) "
                "values (:c, 'citizen', ST_MakePoint(77.59, 12.97)::geography, now())"
            ),
            {"c": code},
        )


def test_tracking_code_check_accepts_good_code(db):
    db.execute(
        text(
            "insert into reports (tracking_code, source, location, captured_at) "
            "values ('RS-7K2Q', 'citizen', ST_MakePoint(77.59, 12.97)::geography, now())"
        )
    )


def test_updated_at_trigger_exists_on_mutable_tables(db):
    rows = db.execute(
        text("select tgname from pg_trigger where tgname like '%_updated_at'")
    ).scalars()
    assert {"defects_updated_at", "reports_updated_at", "surveys_updated_at"} <= set(rows)
