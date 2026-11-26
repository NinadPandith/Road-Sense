"""B7: location helpers: pilot area check, ward, nearby school/hospital, OSM road class."""

import json
import logging
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import httpx
from shapely.geometry import LineString, Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.prepared import PreparedGeometry, prep
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import RoadClass

log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ROAD_SEARCH_RADIUS_M = 20
EARTH_RADIUS_M = 6_371_000

HIGHWAY_TO_CLASS: dict[str, RoadClass] = {
    "motorway": RoadClass.major,
    "trunk": RoadClass.major,
    "primary": RoadClass.major,
    "secondary": RoadClass.secondary,
    "tertiary": RoadClass.tertiary,
    "residential": RoadClass.residential,
    "living_street": RoadClass.residential,
    "unclassified": RoadClass.residential,
    "service": RoadClass.residential,
}


def road_class_for(highway: str | None) -> RoadClass:
    if not highway:
        return RoadClass.unknown
    return HIGHWAY_TO_CLASS.get(highway.removesuffix("_link"), RoadClass.unknown)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


# ---- pilot area ---------------------------------------------------------------------------


@lru_cache
def _pilot_area(path: str) -> PreparedGeometry | None:
    if not path or not Path(path).exists():
        return None
    data = json.loads(Path(path).read_text())
    feats = data["features"] if data.get("type") == "FeatureCollection" else [data]
    geom: BaseGeometry = shape(feats[0]["geometry"])
    for f in feats[1:]:
        geom = geom.union(shape(f["geometry"]))
    return prep(geom)


def in_pilot_area(lat: float, lon: float) -> bool:
    """True when no pilot area is configured, so local development never blocks reports."""
    area = _pilot_area(get_settings().pilot_area_path)
    return True if area is None else area.contains(Point(lon, lat))


# ---- database lookups (Backend Schema queries 3 and 4) --------------------------------------


def find_ward(db: Session, lat: float, lon: float) -> int | None:
    return db.execute(
        text(
            "select id from wards "
            "where ST_Covers(boundary, ST_MakePoint(:lon, :lat)::geography) limit 1"
        ),
        {"lat": lat, "lon": lon},
    ).scalar()


def find_sensitive_place(
    db: Session, lat: float, lon: float, radius_m: float
) -> tuple[int, str] | None:
    row = db.execute(
        text(
            "select id, kind from sensitive_places "
            "where ST_DWithin(location, ST_MakePoint(:lon, :lat)::geography, :r) "
            "order by ST_Distance(location, ST_MakePoint(:lon, :lat)::geography) limit 1"
        ),
        {"lat": lat, "lon": lon, "r": radius_m},
    ).first()
    return (row[0], row[1]) if row else None


# ---- OSM road lookup ----------------------------------------------------------------------


@dataclass(frozen=True)
class RoadInfo:
    road_class: RoadClass
    name: str | None = None
    osm_way_id: int | None = None


UNKNOWN_ROAD = RoadInfo(RoadClass.unknown)


def _metres_xy(lat0: float, lon0: float, lat: float, lon: float) -> tuple[float, float]:
    x = math.radians(lon - lon0) * EARTH_RADIUS_M * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * EARTH_RADIUS_M
    return x, y


def nearest_way(lat: float, lon: float, elements: list[dict]) -> RoadInfo:
    """Pick the way whose line passes closest to the point."""
    best: tuple[float, RoadInfo] | None = None
    for el in elements:
        geom = el.get("geometry") or []
        if el.get("type") != "way" or len(geom) < 2:
            continue
        line = LineString([_metres_xy(lat, lon, g["lat"], g["lon"]) for g in geom])
        d = line.distance(Point(0, 0))
        tags = el.get("tags", {})
        info = RoadInfo(road_class_for(tags.get("highway")), tags.get("name"), el.get("id"))
        if best is None or d < best[0]:
            best = (d, info)
    return best[1] if best else UNKNOWN_ROAD


@lru_cache(maxsize=4096)
def _overpass_road(lat_r: float, lon_r: float) -> RoadInfo:
    query = (
        f"[out:json][timeout:15];way(around:{ROAD_SEARCH_RADIUS_M},{lat_r},{lon_r})[highway];"
        "out tags geom;"
    )
    r = httpx.post(
        OVERPASS_URL, data={"data": query}, timeout=20, headers={"User-Agent": "RoadSense/0.1"}
    )
    r.raise_for_status()
    return nearest_way(lat_r, lon_r, r.json().get("elements", []))


def lookup_road(lat: float, lon: float) -> RoadInfo:
    """Nearest OSM road within 20 m; cached by rounded coordinates; failures give unknown."""
    if not get_settings().osm_lookup_enabled:
        return UNKNOWN_ROAD
    try:
        return _overpass_road(round(lat, 4), round(lon, 4))
    except Exception as exc:  # noqa: BLE001 - network failures must never block a report
        log.warning("Overpass lookup failed: %s", exc)
        return UNKNOWN_ROAD
