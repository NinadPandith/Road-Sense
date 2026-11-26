"""Engineer endpoints: defects, repair list, status changes, stats, settings, nightly job."""

import csv
import io
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.api.deps import get_scoring_settings, get_services
from app.api.reports import read_limited
from app.core.auth import Staff, get_staff, require_cron, require_engineer
from app.core.db import get_db
from app.core.errors import ApiError
from app.models import Defect, Detection, Profile, SettingsVersion, StatusHistory
from app.models.enums import (
    OPEN_STATUSES,
    DamageClass,
    DefectStatus,
    RoadClass,
    SeverityLabel,
)
from app.schemas.defects import (
    BulkStatusIn,
    BulkStatusOut,
    CountItem,
    DefectDetail,
    DefectListItem,
    DetectionOut,
    HistoryOut,
    Page,
    ReportOut,
    Stats,
    Updated,
    WeekItem,
)
from app.services import images
from app.services import status as status_service
from app.services.defects import recalculate, recalculate_all_open
from app.services.pipeline import Services
from app.services.queries import (
    DefectFilters,
    get_defect_row,
    list_defects,
    parse_bbox,
    row_to_item,
)
from app.services.settings import SettingsValues
from app.services.storage import FIXED_PHOTOS, REPORT_IMAGES

router = APIRouter(tags=["engineer"])


def defect_filters(
    status: Annotated[list[DefectStatus] | None, Query()] = None,
    severity: Annotated[list[SeverityLabel] | None, Query()] = None,
    ward_id: Annotated[list[int] | None, Query()] = None,
    road_class: Annotated[list[RoadClass] | None, Query()] = None,
    damage_class: Annotated[list[DamageClass] | None, Query()] = None,
    survey_id: uuid.UUID | None = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    bbox: str | None = None,
) -> DefectFilters:
    return DefectFilters(
        status=status or list(OPEN_STATUSES),
        severity=severity or [],
        ward_id=ward_id or [],
        road_class=road_class or [],
        damage_class=damage_class or [],
        survey_id=survey_id,
        date_from=date_from,
        date_to=date_to,
        bbox=parse_bbox(bbox),
    )


class Me(BaseModel):
    id: uuid.UUID
    full_name: str
    role: str


@router.get("/me", response_model=Me)
def me(staff: Staff = Depends(get_staff)) -> Me:
    return Me(id=staff.id, full_name=staff.full_name, role=staff.role.value)


@router.get("/defects", response_model=Page[DefectListItem])
def get_defects(
    filters: DefectFilters = Depends(defect_filters),
    sort: str = "priority",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    _: Staff = Depends(get_staff),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> Page[DefectListItem]:
    items, total = list_defects(db, services.storage, filters, sort, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


def _detail(
    db: Session, services: Services, defect_id: uuid.UUID, scoring: SettingsValues
) -> DefectDetail:
    row = get_defect_row(db, defect_id)
    item = row_to_item(row, services.storage, datetime.now(UTC))
    m = row._mapping
    url = services.storage.public_url

    reports = db.execute(
        text(
            "select id, tracking_code, source, image_path, note, created_at, "
            "ST_Y(location::geometry) as lat, ST_X(location::geometry) as lon "
            "from reports where defect_id = :id order by created_at desc"
        ),
        {"id": defect_id},
    ).all()
    dets_by_report: dict[uuid.UUID, list[DetectionOut]] = {}
    report_ids = [r.id for r in reports]
    if report_ids:
        for d in db.scalars(select(Detection).where(Detection.report_id.in_(report_ids))):
            dets_by_report.setdefault(d.report_id, []).append(
                DetectionOut(
                    damage_class=d.damage_class,
                    confidence=d.confidence,
                    box=list(d.box),
                    size_score=d.size_score,
                    depth_score=d.depth_score,
                    type_score=d.type_score,
                    position_score=d.position_score,
                    severity_score=d.severity_score,
                    severity_label=d.severity_label,
                )
            )
    history = db.execute(
        select(StatusHistory, Profile.full_name)
        .outerjoin(Profile, Profile.id == StatusHistory.changed_by)
        .where(StatusHistory.defect_id == defect_id)
        .order_by(StatusHistory.created_at.desc(), StatusHistory.id.desc())
    ).all()
    sensitive = None
    if m["sensitive_kind"]:
        sensitive = m["sensitive_kind"] + (
            f": {m['sensitive_name']}" if m["sensitive_name"] else ""
        )
    return DefectDetail(
        **item.model_dump(),
        priority_terms=m["priority_terms"],
        sensitive_place=sensitive,
        reopened_count=m["reopened_count"],
        fixed_at=m["fixed_at"],
        fixed_photo_url=url(FIXED_PHOTOS, m["fixed_photo_path"]) if m["fixed_photo_path"] else None,
        reports=[
            ReportOut(
                id=r.id,
                tracking_code=r.tracking_code,
                source=r.source,
                lat=r.lat,
                lon=r.lon,
                image_url=url(REPORT_IMAGES, r.image_path) if r.image_path else None,
                note=r.note,
                detections=sorted(
                    dets_by_report.get(r.id, []), key=lambda d: d.severity_score, reverse=True
                ),
                created_at=r.created_at,
            )
            for r in reports
        ],
        history=[
            HistoryOut(
                from_status=h.from_status,
                to_status=h.to_status,
                changed_by=name,
                reason=h.reason,
                created_at=h.created_at,
            )
            for h, name in history
        ],
        merge_radius_m=scoring.merge_radius_m,
    )


@router.get("/defects/{defect_id}", response_model=DefectDetail)
def get_defect(
    defect_id: uuid.UUID,
    _: Staff = Depends(get_staff),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
    scoring: SettingsValues = Depends(get_scoring_settings),
) -> DefectDetail:
    return _detail(db, services, defect_id, scoring)


@router.patch("/defects/{defect_id}/status", response_model=DefectDetail)
async def patch_status(
    defect_id: uuid.UUID,
    to_status: DefectStatus = Form(...),
    reason: str | None = Form(None, max_length=200),
    fixed_photo: UploadFile | None = File(None),
    damage_class: DamageClass | None = Form(None),
    severity_label: SeverityLabel | None = Form(None),
    staff: Staff = Depends(require_engineer),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
    scoring: SettingsValues = Depends(get_scoring_settings),
) -> DefectDetail:
    defect = db.get(Defect, defect_id, with_for_update=True)
    if defect is None:
        raise ApiError("not_found", 404, "No defect found with this ID.")
    photo_path = None
    if fixed_photo is not None and to_status == DefectStatus.fixed:
        rgb = images.load_image(await read_limited(fixed_photo, 50))
        from app.services.privacy import anonymise

        rgb, _ = anonymise(rgb)
        photo_path = f"{defect.id}/{datetime.now(UTC):%Y%m%dT%H%M%S}.jpg"
        services.storage.upload(FIXED_PHOTOS, photo_path, images.encode_jpeg(rgb), "image/jpeg")
    was_review = defect.status == DefectStatus.needs_review
    status_service.change_status(db, defect, to_status, staff.id, reason, photo_path)
    if was_review and to_status == DefectStatus.reported:
        # Accept: the engineer says what the AI couldn't (B11).
        status_service.accept_review(defect, damage_class, severity_label)
        recalculate(db, defect, scoring)
    db.flush()
    return _detail(db, services, defect_id, scoring)


@router.post("/defects/bulk-status", response_model=BulkStatusOut)
def bulk_status(
    body: BulkStatusIn,
    staff: Staff = Depends(require_engineer),
    db: Session = Depends(get_db),
) -> BulkStatusOut:
    defects = db.scalars(select(Defect).where(Defect.id.in_(body.ids)).with_for_update()).all()
    updated, skipped = 0, [i for i in body.ids if i not in {d.id for d in defects}]
    for d in defects:
        if status_service.can_transition(d.status, body.to_status):
            status_service.change_status(db, d, body.to_status, staff.id, body.reason)
            updated += 1
        else:
            skipped.append(d.id)
    db.flush()
    return BulkStatusOut(updated=updated, skipped=skipped)


CSV_COLUMNS = [
    "rank",
    "id",
    "damage_type",
    "severity",
    "severity_score",
    "priority",
    "reason",
    "road",
    "road_type",
    "ward",
    "reports",
    "age_days",
    "status",
    "lat",
    "lon",
    "map_link",
    "photo",
]


@router.get("/repair-list.csv")
def repair_list_csv(
    filters: DefectFilters = Depends(defect_filters),
    sort: str = "priority",
    _: Staff = Depends(get_staff),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> StreamingResponse:
    items: list[DefectListItem] = []
    page = 1
    while True:
        batch, total = list_defects(db, services.storage, filters, sort, page, 100)
        items.extend(batch)
        if len(items) >= total or not batch:
            break
        page += 1
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(CSV_COLUMNS)
    for d in items:
        w.writerow(
            [
                d.rank or "",
                d.id,
                d.damage_class.value if d.damage_class else "",
                d.severity_label.value if d.severity_label else "",
                f"{d.severity_score:.2f}" if d.severity_score is not None else "",
                f"{d.priority:.2f}",
                d.priority_reason,
                d.road_name or "",
                d.road_class.value,
                d.ward.name if d.ward else "",
                d.report_count,
                d.age_days,
                d.status.value,
                f"{d.lat:.6f}",
                f"{d.lon:.6f}",
                f"https://www.openstreetmap.org/?mlat={d.lat:.6f}&mlon={d.lon:.6f}#map=19/{d.lat:.6f}/{d.lon:.6f}",
                d.thumb_url or "",
            ]
        )
    filename = f"roadsense-repair-list-{datetime.now(UTC):%Y-%m-%d}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/stats", response_model=Stats)
def stats(
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    _: Staff = Depends(get_staff),
    db: Session = Depends(get_db),
) -> Stats:
    now = datetime.now(UTC)
    week_ago = now - timedelta(days=7)
    open_sql = "status in ('needs_review', 'reported', 'verified', 'assigned')"
    one = db.execute(
        text(
            f"""
            select
              count(*) filter (where {open_sql}) as open_defects,
              count(*) filter (where {open_sql} and severity_label = 'dangerous') as dangerous,
              count(*) filter (where first_reported_at >= :wk) as new_week,
              count(*) filter (where status = 'fixed' and fixed_at >= :wk) as fixed_week,
              count(*) filter (where status = 'needs_review') as needs_review
            from defects
            """
        ),
        {"wk": week_ago},
    ).one()
    by_sev = db.execute(
        text(
            f"select coalesce(severity_label::text, 'unscored') k, count(*) c from defects "
            f"where {open_sql} group by 1 order by 2 desc"
        )
    ).all()
    by_ward = db.execute(
        text(
            f"select coalesce(w.name, 'No ward') k, count(*) c from defects d "
            f"left join wards w on w.id = d.ward_id where d.{open_sql} group by 1 order by 2 desc"
        )
    ).all()
    start = date_from or (now - timedelta(weeks=8))
    end = date_to or now
    weeks = db.execute(
        text(
            """
            with w as (
              select generate_series(date_trunc('week', cast(:s as timestamptz)),
                                     date_trunc('week', cast(:e as timestamptz)),
                                     interval '1 week') as wk
            )
            select to_char(w.wk, 'YYYY-MM-DD') wk,
              (select count(*) from defects d where d.status = 'fixed'
                 and d.fixed_at >= w.wk and d.fixed_at < w.wk + interval '1 week') fixed,
              (select count(*) from defects d
                 where d.first_reported_at >= w.wk
                   and d.first_reported_at < w.wk + interval '1 week') reported
            from w order by w.wk
            """
        ),
        {"s": start, "e": end},
    ).all()
    return Stats(
        open_defects=one.open_defects,
        dangerous_open=one.dangerous,
        new_this_week=one.new_week,
        fixed_this_week=one.fixed_week,
        needs_review=one.needs_review,
        open_by_severity=[CountItem(key=r.k, count=r.c) for r in by_sev],
        open_by_ward=[CountItem(key=r.k, count=r.c) for r in by_ward],
        per_week=[WeekItem(week_start=r.wk, fixed=r.fixed, reported=r.reported) for r in weeks],
    )


@router.get("/settings", response_model=SettingsValues)
def get_scoring(
    _: Staff = Depends(get_staff), scoring: SettingsValues = Depends(get_scoring_settings)
) -> SettingsValues:
    return scoring


@router.post("/settings", response_model=SettingsValues)
def save_scoring(
    body: SettingsValues,
    staff: Staff = Depends(require_engineer),
    db: Session = Depends(get_db),
) -> SettingsValues:
    """Every change is a new version (audit trail) and triggers a priority recalculation."""
    db.add(SettingsVersion(values=body.model_dump(), created_by=staff.id))
    db.flush()
    recalculate_all_open(db, body)
    return body


@router.post("/admin/recalculate", response_model=Updated, dependencies=[Depends(require_cron)])
def nightly_recalculate(
    db: Session = Depends(get_db), scoring: SettingsValues = Depends(get_scoring_settings)
) -> Updated:
    """Nightly job: the age term grows every day; also clears IP hashes older than 30 days."""
    n = recalculate_all_open(db, scoring)
    db.execute(
        text(
            "update reports set ip_hash = null "
            "where ip_hash is not null and created_at < now() - interval '30 days'"
        )
    )
    return Updated(updated=n)
