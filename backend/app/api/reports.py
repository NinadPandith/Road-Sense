"""Citizen endpoints: POST /reports, POST /reports/{code}/send-anyway, GET /track/{code}."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_ip_hash, get_scoring_settings, get_services
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.models import Defect, Report, StatusHistory
from app.models.enums import DefectStatus, ReportSource
from app.schemas.reports import ReportResult, TimelineStep, TrackResult
from app.services.codes import normalise_code
from app.services.pipeline import ReportInput, Services, process_report, send_anyway
from app.services.settings import SettingsValues
from app.services.storage import FIXED_PHOTOS, REPORT_IMAGES

router = APIRouter(tags=["citizen"])

CHUNK = 1024 * 1024


async def read_limited(upload: UploadFile, max_mb: int) -> bytes:
    limit = max_mb * 1024 * 1024
    data = bytearray()
    while chunk := await upload.read(CHUNK):
        data.extend(chunk)
        if len(data) > limit:
            raise ApiError("invalid_image", 413, f"Files can be up to {max_mb} MB.")
    return bytes(data)


@router.post("/reports", response_model=ReportResult)
async def create_report(
    image: UploadFile = File(...),
    lat: float = Form(..., ge=-90, le=90),
    lon: float = Form(..., ge=-180, le=180),
    captured_at: datetime | None = Form(None),
    source: ReportSource = Form(ReportSource.citizen),
    accuracy_m: float | None = Form(None, ge=0),
    note: str | None = Form(None, max_length=200),
    client_report_id: uuid.UUID | None = Form(None),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
    scoring: SettingsValues = Depends(get_scoring_settings),
    ip_hash: str = Depends(get_ip_hash),
) -> ReportResult:
    if source == ReportSource.survey:
        raise ApiError("validation_error", 422, "Survey frames are uploaded through /surveys.")
    settings = get_settings()
    data = await read_limited(image, settings.max_upload_mb)
    inp = ReportInput(
        lat=lat,
        lon=lon,
        captured_at=captured_at or datetime.now(UTC),
        source=source,
        accuracy_m=accuracy_m,
        note=note.strip() if note else None,
        client_report_id=client_report_id,
        ip_hash=ip_hash,
    )
    return process_report(db, services, scoring, data, inp, settings.rate_limit_per_hour)


def _report_by_code(db: Session, code: str) -> Report:
    report = db.scalar(select(Report).where(Report.tracking_code == normalise_code(code)))
    if report is None:
        raise ApiError("not_found", 404)
    return report


@router.post("/reports/{code}/send-anyway", response_model=ReportResult)
def send_report_anyway(
    code: str,
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
    scoring: SettingsValues = Depends(get_scoring_settings),
) -> ReportResult:
    return send_anyway(db, services, scoring, _report_by_code(db, code))


TIMELINE = (DefectStatus.reported, DefectStatus.verified, DefectStatus.assigned, DefectStatus.fixed)


@router.get("/track/{code}", response_model=TrackResult)
def track(
    code: str, db: Session = Depends(get_db), services: Services = Depends(get_services)
) -> TrackResult:
    report = _report_by_code(db, code)
    url = services.storage.public_url
    res = TrackResult(
        tracking_code=report.tracking_code,
        report_status=report.status,
        created_at=report.created_at,
        image_url=url(REPORT_IMAGES, report.image_path) if report.image_path else None,
        thumb_url=url(REPORT_IMAGES, report.thumb_path) if report.thumb_path else None,
    )
    if report.defect_id is None:
        return res
    defect = db.get(Defect, report.defect_id)
    assert defect is not None
    res.defect_status = defect.status
    res.damage_class = defect.damage_class
    res.severity_label = defect.severity_label
    res.report_count = defect.report_count
    if defect.fixed_photo_path and defect.status == DefectStatus.fixed:
        res.fixed_photo_url = url(FIXED_PHOTOS, defect.fixed_photo_path)

    # Timeline: the latest date each step was reached, from the status history.
    reached: dict[DefectStatus, datetime] = {DefectStatus.reported: report.created_at}
    for h in db.scalars(
        select(StatusHistory)
        .where(StatusHistory.defect_id == defect.id)
        .order_by(StatusHistory.created_at)
    ):
        if h.to_status in TIMELINE and h.to_status != DefectStatus.reported:
            reached[h.to_status] = h.created_at
    order = {s: i for i, s in enumerate(TIMELINE)}
    current = order.get(defect.status, 0)
    res.timeline = [
        TimelineStep(status=s, at=reached.get(s) if order[s] <= current else None) for s in TIMELINE
    ]
    return res
