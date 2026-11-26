"""B6: merge a report into an existing defect within the merge radius, or create a new one.

Backend Schema, core query 1. Runs inside the request's transaction:
- area advisory locks stop two simultaneous reports of one pothole from creating two defects;
- `for update` locks the matched defect row while its counters change.
"""

import math
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Defect, Report, StatusHistory
from app.models.enums import DamageClass, DefectStatus, SeverityLabel
from app.services.settings import SettingsValues

LOCK_CELL_DEG = 0.001  # ~111 m; much larger than any merge radius we allow (<= 50 m)


@dataclass(frozen=True)
class Finding:
    """What the AI found in a report (None fields for a 'send anyway' report)."""

    damage_class: DamageClass | None
    severity_score: float | None
    severity_label: SeverityLabel | None


@dataclass
class MergeOutcome:
    defect: Defect
    is_new: bool
    reopened: bool = False
    auto_verified: bool = False


def point_wkt(lat: float, lon: float) -> str:
    return f"SRID=4326;POINT({lon} {lat})"


def lock_area(db: Session, lat: float, lon: float, radius_m: float) -> None:
    """Take transaction-level advisory locks on every grid cell the merge circle touches."""
    dlat = radius_m / 111_320
    dlon = radius_m / (111_320 * max(0.01, math.cos(math.radians(lat))))
    cells = sorted(
        {
            (
                math.floor((lat + sy * dlat) / LOCK_CELL_DEG),
                math.floor((lon + sx * dlon) / LOCK_CELL_DEG),
            )
            for sy in (-1, 1)
            for sx in (-1, 1)
        }
    )
    for cy, cx in cells:
        db.execute(text("select pg_advisory_xact_lock(:a, :b)"), {"a": cy, "b": cx})


def find_mergeable(
    db: Session, lat: float, lon: float, settings: SettingsValues
) -> uuid.UUID | None:
    return db.execute(
        text(
            """
            select id from defects
            where ST_DWithin(location, ST_MakePoint(:lon, :lat)::geography, :radius_m)
              and (status in ('needs_review', 'reported', 'verified', 'assigned')
                   or (status = 'fixed'
                       and fixed_at > now() - make_interval(days => :reopen_days)))
            order by ST_Distance(location, ST_MakePoint(:lon, :lat)::geography)
            limit 1
            for update
            """
        ),
        {
            "lat": lat,
            "lon": lon,
            "radius_m": settings.merge_radius_m,
            "reopen_days": settings.reopen_days,
        },
    ).scalar()


def _history(db: Session, defect_id: uuid.UUID, frm, to, reason: str) -> None:
    db.add(StatusHistory(defect_id=defect_id, from_status=frm, to_status=to, reason=reason))


def merge_report(
    db: Session,
    report: Report,
    lat: float,
    lon: float,
    finding: Finding,
    settings: SettingsValues,
    now: datetime,
) -> MergeOutcome:
    lock_area(db, lat, lon, settings.merge_radius_m)
    defect_id = find_mergeable(db, lat, lon, settings)

    if defect_id is None:
        status = DefectStatus.reported if finding.damage_class else DefectStatus.needs_review
        defect = Defect(
            location=point_wkt(lat, lon),
            damage_class=finding.damage_class,
            severity_score=finding.severity_score,
            severity_label=finding.severity_label,
            report_count=1,
            status=status,
            first_reported_at=now,
            last_reported_at=now,
            priority_terms={},
        )
        db.add(defect)
        db.flush()
        _history(db, defect.id, None, status, "first report")
        report.defect_id = defect.id
        db.flush()
        return MergeOutcome(defect=defect, is_new=True)

    defect = db.get(Defect, defect_id, populate_existing=True)
    assert defect is not None
    out = MergeOutcome(defect=defect, is_new=False)
    defect.report_count += 1
    defect.last_reported_at = now

    if finding.severity_score is not None and (
        defect.severity_score is None or finding.severity_score > defect.severity_score
    ):
        defect.severity_score = finding.severity_score
        defect.severity_label = finding.severity_label
        defect.damage_class = finding.damage_class

    if defect.status == DefectStatus.fixed:
        _history(
            db, defect.id, DefectStatus.fixed, DefectStatus.reported, "re-opened by new report"
        )
        defect.status = DefectStatus.reported
        defect.reopened_count += 1
        defect.fixed_at = None
        out.reopened = True
    elif defect.status == DefectStatus.needs_review and finding.damage_class is not None:
        _history(
            db,
            defect.id,
            DefectStatus.needs_review,
            DefectStatus.reported,
            "AI found damage in a new report",
        )
        defect.status = DefectStatus.reported

    if (
        defect.status == DefectStatus.reported
        and defect.report_count >= settings.auto_verify_reports
    ):
        _history(
            db,
            defect.id,
            DefectStatus.reported,
            DefectStatus.verified,
            f"{defect.report_count} reports",
        )
        defect.status = DefectStatus.verified
        defect.verified_at = now
        out.auto_verified = True

    report.defect_id = defect.id
    db.flush()
    # Move the defect to the average position of all its reports.
    db.execute(
        text(
            """
            update defects set location = (
              select ST_Centroid(ST_Collect(r.location::geometry))::geography
              from reports r where r.defect_id = :id)
            where id = :id
            """
        ),
        {"id": defect.id},
    )
    db.refresh(defect)
    return out
