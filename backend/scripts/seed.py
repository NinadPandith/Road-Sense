"""Seed a fresh database (docs/backend-schema.md, "Seed data").

Usage (from backend/):
    uv run python -m scripts.seed                       # settings v1 + any GeoJSON files present
    uv run python -m scripts.seed --fetch-osm           # also fetch schools/hospitals from Overpass
    uv run python -m scripts.seed --users               # also create engineer + demo users

Files read from the repo's data/ folder when present:
    data/pilot_area.geojson        pilot area polygon (used for the bbox of the Overpass query)
    data/wards.geojson             features with properties {code, name}
    data/sensitive_places.geojson  features with properties {kind, name, osm_id}
Users need env vars: ENGINEER_EMAIL, ENGINEER_PASSWORD, DEMO_EMAIL, DEMO_PASSWORD
plus SUPABASE_URL and SUPABASE_SERVICE_KEY.
"""

import argparse
import json
import os
import pathlib
import sys

import httpx
from shapely.geometry import MultiPolygon, shape
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_sessionmaker
from app.models import SettingsVersion
from app.services.settings import DEFAULT_SETTINGS

DATA = pathlib.Path(__file__).resolve().parents[2] / "data"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def seed_settings(db: Session) -> None:
    if db.scalar(select(func.count()).select_from(SettingsVersion)):
        print("settings: already present, skipped")
        return
    db.add(SettingsVersion(values=DEFAULT_SETTINGS.model_dump()))
    print("settings: v1 inserted")


def _features(path: pathlib.Path) -> list[dict]:
    return json.loads(path.read_text())["features"]


def seed_wards(db: Session, path: pathlib.Path) -> None:
    if not path.exists():
        print(f"wards: {path.name} not found, skipped")
        return
    n = 0
    for f in _features(path):
        geom = shape(f["geometry"])
        if geom.geom_type == "Polygon":
            geom = MultiPolygon([geom])
        props = f.get("properties") or {}
        db.execute(
            text(
                "insert into wards (code, name, boundary) "
                "values (:code, :name, ST_GeogFromText(:wkt)) "
                "on conflict (code) do update "
                "set name = excluded.name, boundary = excluded.boundary"
            ),
            {
                "code": str(props["code"]),
                "name": props.get("name") or props["code"],
                "wkt": geom.wkt,
            },
        )
        n += 1
    print(f"wards: {n} upserted")


def _upsert_place(db: Session, kind: str, name: str | None, osm_id: int, lon: float, lat: float):
    db.execute(
        text(
            "insert into sensitive_places (kind, name, osm_id, location) "
            "values (:kind, :name, :osm_id, ST_MakePoint(:lon, :lat)::geography) "
            "on conflict (osm_id) do update set name = excluded.name, location = excluded.location"
        ),
        {"kind": kind, "name": name, "osm_id": osm_id, "lon": lon, "lat": lat},
    )


def seed_places_from_file(db: Session, path: pathlib.Path) -> None:
    if not path.exists():
        print(f"sensitive_places: {path.name} not found, skipped")
        return
    n = 0
    for f in _features(path):
        p = f["properties"]
        pt = shape(f["geometry"]).centroid
        _upsert_place(db, p["kind"], p.get("name"), int(p["osm_id"]), pt.x, pt.y)
        n += 1
    print(f"sensitive_places: {n} upserted from file")


def fetch_places_from_osm(db: Session, pilot_path: pathlib.Path) -> None:
    if not pilot_path.exists():
        sys.exit("pilot_area.geojson is needed for --fetch-osm (draw it on geojson.io)")
    minx, miny, maxx, maxy = shape(_features(pilot_path)[0]["geometry"]).buffer(0.01).bounds
    bbox = f"{miny},{minx},{maxy},{maxx}"
    query = f"""
    [out:json][timeout:60];
    (nwr["amenity"="school"]({bbox}); nwr["amenity"="hospital"]({bbox}););
    out center tags;
    """
    resp = httpx.post(
        OVERPASS_URL, data={"data": query}, timeout=90, headers={"User-Agent": "RoadSense/0.1"}
    )
    resp.raise_for_status()
    n = 0
    for el in resp.json()["elements"]:
        lat = el.get("lat") or el.get("center", {}).get("lat")
        lon = el.get("lon") or el.get("center", {}).get("lon")
        if lat is None:
            continue
        osm_id = {"node": 1, "way": 2, "relation": 3}[el["type"]] * 10**12 + el["id"]
        _upsert_place(db, el["tags"]["amenity"], el["tags"].get("name"), osm_id, lon, lat)
        n += 1
    print(f"sensitive_places: {n} upserted from Overpass")


def seed_users(db: Session) -> None:
    s = get_settings()
    if not (s.supabase_url and s.supabase_service_key):
        sys.exit("SUPABASE_URL and SUPABASE_SERVICE_KEY are needed for --users")
    headers = {
        "apikey": s.supabase_service_key,
        "Authorization": f"Bearer {s.supabase_service_key}",
    }
    for role, full_name in (("engineer", "Engineer"), ("demo", "Demo user")):
        email = os.environ.get(f"{role.upper()}_EMAIL")
        password = os.environ.get(f"{role.upper()}_PASSWORD")
        if not (email and password):
            print(f"users: {role.upper()}_EMAIL/{role.upper()}_PASSWORD not set, skipped {role}")
            continue
        r = httpx.post(
            f"{s.supabase_url}/auth/v1/admin/users",
            headers=headers,
            json={"email": email, "password": password, "email_confirm": True},
            timeout=30,
        )
        if r.status_code == 422:
            user_id = db.scalar(text("select id from auth.users where email = :e"), {"e": email})
        else:
            r.raise_for_status()
            user_id = r.json()["id"]
        db.execute(
            text(
                "insert into profiles (id, full_name, role) values (:id, :n, :r) "
                "on conflict (id) do update set role = excluded.role"
            ),
            {"id": user_id, "n": full_name, "r": role},
        )
        print(f"users: {role} {email} ready")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fetch-osm", action="store_true", help="fetch schools/hospitals")
    parser.add_argument("--users", action="store_true", help="create engineer + demo users")
    args = parser.parse_args()

    with get_sessionmaker()() as db, db.begin():
        seed_settings(db)
        seed_wards(db, DATA / "wards.geojson")
        if args.fetch_osm:
            fetch_places_from_osm(db, DATA / "pilot_area.geojson")
        else:
            seed_places_from_file(db, DATA / "sensitive_places.geojson")
        if args.users:
            seed_users(db)


if __name__ == "__main__":
    main()
