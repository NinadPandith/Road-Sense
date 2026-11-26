"""Shared fixtures.

Database tests (marker `db`) need TEST_DATABASE_URL pointing at an empty Postgres with PostGIS.
The schema is rebuilt once per run with the Alembic migrations, and each test runs inside a
transaction that is rolled back, so tests never see each other's rows.
"""

import os
import pathlib
from collections.abc import Iterator

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from alembic import command
from app.core.db import get_db
from app.main import create_app

BACKEND = pathlib.Path(__file__).resolve().parents[1]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL not set")
    eng = create_engine(TEST_DATABASE_URL)
    with eng.begin() as conn:
        conn.execute(text("drop schema if exists public cascade"))
        conn.execute(text("create schema public"))
        conn.execute(text("grant usage on schema public to public"))
        conn.execute(text((BACKEND / "scripts" / "supabase_shim.sql").read_text()))
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    os.environ["ALEMBIC_DATABASE_URL"] = TEST_DATABASE_URL
    command.upgrade(cfg, "head")
    yield eng
    eng.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    conn = engine.connect()
    trans = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        conn.close()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_client(app, db: Session) -> TestClient:
    def _get_db() -> Iterator[Session]:
        yield db
        db.flush()

    app.dependency_overrides[get_db] = _get_db
    return TestClient(app)
