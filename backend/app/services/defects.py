"""B7 + B8: enrich a new defect and keep its priority up to date."""

from datetime import UTC, datetime

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Defect, SensitivePlace
from app.models.enums import OPEN_STATUSES
from app.services import geo
from app.services.priority import compute_priority, days_open, priority_reason
from app.services.settings import SettingsValues


def defect_latlon(db: Session, defect: Defect) -> tuple[float, float]:
    row = db.execute(
        text(
            "select ST_Y(location::geometry), ST_X(location::geometry) from defects where id = :id"
        ),
        {"id": defect.id},
    ).one()
    return float(row[0]), float(row[1])


def enrich(db: Session, defect: Defect, settings: SettingsValues, road_lookup=geo.lookup_road):
    """Ward, nearest school/hospital within the sensitive radius, and OSM road class."""
    lat, lon = defect_latlon(db, defect)
    defect.ward_id = geo.find_ward(db, lat, lon)
    place = geo.find_sensitive_place(db, lat, lon, settings.sensitive_radius_m)
    defect.near_sensitive = place is not None
    defect.sensitive_place_id = place[0] if place else None
    road = road_lookup(lat, lon)
    defect.road_class = road.road_class
    defect.road_name = road.name
    defect.osm_way_id = road.osm_way_id


def recalculate(
    db: Session, defect: Defect, settings: SettingsValues, now: datetime | None = None
) -> None:
    now = now or datetime.now(UTC)
    result = compute_priority(
        defect.severity_score,
        defect.road_class,
        defect.report_count,
        days_open(defect.first_reported_at, now),
        defect.near_sensitive,
        settings,
    )
    defect.priority = result.priority
    defect.priority_terms = result.terms


def recalculate_all_open(db: Session, settings: SettingsValues) -> int:
    now = datetime.now(UTC)
    defects = db.scalars(select(Defect).where(Defect.status.in_(OPEN_STATUSES))).all()
    for d in defects:
        recalculate(db, d, settings, now)
    db.flush()
    return len(defects)


def reason_for(db: Session, defect: Defect, now: datetime | None = None) -> str:
    now = now or datetime.now(UTC)
    kind = None
    if defect.sensitive_place_id:
        kind = db.scalar(
            select(SensitivePlace.kind).where(SensitivePlace.id == defect.sensitive_place_id)
        )
    return priority_reason(
        defect.severity_label,
        defect.road_class,
        kind,
        defect.report_count,
        days_open(defect.first_reported_at, now),
    )
