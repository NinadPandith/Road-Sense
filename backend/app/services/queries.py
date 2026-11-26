"""Read queries for the dashboard, repair list and defect detail."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models.enums import (
    OPEN_STATUSES,
    DamageClass,
    DefectStatus,
    RoadClass,
    SeverityLabel,
)
from app.schemas.defects import DefectListItem, WardOut
from app.services.priority import days_open, priority_reason
from app.services.storage import REPORT_IMAGES, Storage

SORTS = {
    "priority": "d.priority desc, d.first_reported_at",
    "-priority": "d.priority asc",
    "severity": "d.severity_score desc nulls last",
    "age": "d.first_reported_at asc",
    "-age": "d.first_reported_at desc",
    "reports": "d.report_count desc",
    "updated": "d.updated_at desc",
}


@dataclass
class DefectFilters:
    status: list[DefectStatus] = field(default_factory=lambda: list(OPEN_STATUSES))
    severity: list[SeverityLabel] = field(default_factory=list)
    ward_id: list[int] = field(default_factory=list)
    road_class: list[RoadClass] = field(default_factory=list)
    damage_class: list[DamageClass] = field(default_factory=list)
    survey_id: uuid.UUID | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    bbox: tuple[float, float, float, float] | None = None  # min_lon, min_lat, max_lon, max_lat
    ids: list[uuid.UUID] = field(default_factory=list)


def parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if not value:
        return None
    try:
        parts = tuple(float(v) for v in value.split(","))
    except ValueError as exc:
        raise ApiError(
            "validation_error", 422, "bbox must be min_lon,min_lat,max_lon,max_lat"
        ) from exc
    if len(parts) != 4:
        raise ApiError("validation_error", 422, "bbox must be min_lon,min_lat,max_lon,max_lat")
    return parts  # type: ignore[return-value]


BASE = """
with ranked as (
  select id, rank() over (order by priority desc, first_reported_at) as rnk
  from defects where status in ('needs_review', 'reported', 'verified', 'assigned')
)
select d.*, ST_Y(d.location::geometry) as lat, ST_X(d.location::geometry) as lon,
       w.name as ward_name, sp.kind as sensitive_kind, sp.name as sensitive_name, rk.rnk,
       (select r.thumb_path from reports r where r.defect_id = d.id and r.thumb_path is not null
         order by r.created_at desc limit 1) as thumb_path,
       count(*) over () as total
from defects d
left join wards w on w.id = d.ward_id
left join sensitive_places sp on sp.id = d.sensitive_place_id
left join ranked rk on rk.id = d.id
"""


def _where(f: DefectFilters) -> tuple[str, dict]:
    clauses, params = [], {}
    if f.status:
        clauses.append("d.status::text = any(:status)")
        params["status"] = [s.value for s in f.status]
    if f.severity:
        clauses.append("d.severity_label::text = any(:severity)")
        params["severity"] = [s.value for s in f.severity]
    if f.ward_id:
        clauses.append("d.ward_id = any(:ward_id)")
        params["ward_id"] = f.ward_id
    if f.road_class:
        clauses.append("d.road_class::text = any(:road_class)")
        params["road_class"] = [r.value for r in f.road_class]
    if f.damage_class:
        clauses.append("d.damage_class::text = any(:damage_class)")
        params["damage_class"] = [c.value for c in f.damage_class]
    if f.survey_id:
        clauses.append(
            "exists (select 1 from reports r where r.defect_id = d.id and r.survey_id = :survey)"
        )
        params["survey"] = f.survey_id
    if f.date_from:
        clauses.append("d.first_reported_at >= :dfrom")
        params["dfrom"] = f.date_from
    if f.date_to:
        clauses.append("d.first_reported_at < :dto")
        params["dto"] = f.date_to
    if f.bbox:
        clauses.append("ST_Intersects(d.location, ST_MakeEnvelope(:x1, :y1, :x2, :y2, 4326))")
        params.update(dict(zip(("x1", "y1", "x2", "y2"), f.bbox, strict=True)))
    if f.ids:
        clauses.append("d.id = any(:ids)")
        params["ids"] = f.ids
    return ("where " + " and ".join(clauses)) if clauses else "", params


def row_to_item(row, storage: Storage, now: datetime) -> DefectListItem:
    m = row._mapping
    age = days_open(m["first_reported_at"], now)
    return DefectListItem(
        id=m["id"],
        rank=m["rnk"],
        lat=m["lat"],
        lon=m["lon"],
        damage_class=m["damage_class"],
        severity_label=m["severity_label"],
        severity_score=m["severity_score"],
        priority=m["priority"],
        priority_reason=priority_reason(
            SeverityLabel(m["severity_label"]) if m["severity_label"] else None,
            RoadClass(m["road_class"]),
            m["sensitive_kind"],
            m["report_count"],
            age,
        ),
        road_class=m["road_class"],
        road_name=m["road_name"],
        ward=WardOut(id=m["ward_id"], name=m["ward_name"]) if m["ward_id"] else None,
        report_count=m["report_count"],
        age_days=age,
        status=m["status"],
        near_sensitive=m["near_sensitive"],
        first_reported_at=m["first_reported_at"],
        thumb_url=storage.public_url(REPORT_IMAGES, m["thumb_path"]) if m["thumb_path"] else None,
    )


def list_defects(
    db: Session,
    storage: Storage,
    f: DefectFilters,
    sort: str = "priority",
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[DefectListItem], int]:
    where, params = _where(f)
    order = SORTS.get(sort, SORTS["priority"])
    sql = f"{BASE} {where} order by {order} limit :limit offset :offset"
    params.update(limit=page_size, offset=(page - 1) * page_size)
    rows = db.execute(text(sql), params).all()
    now = datetime.now(UTC)
    total = rows[0]._mapping["total"] if rows else 0
    return [row_to_item(r, storage, now) for r in rows], total


def get_defect_row(db: Session, defect_id: uuid.UUID):
    row = db.execute(text(f"{BASE} where d.id = :id"), {"id": defect_id}).first()
    if row is None:
        raise ApiError("not_found", 404, "No defect found with this ID.")
    return row
