"""A5 Surveys: upload a ride video + GPX track; processed by the survey worker."""

import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_services
from app.api.reports import read_limited
from app.core.auth import Staff, get_staff, require_engineer
from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.models import Survey
from app.schemas.surveys import SurveyOut
from app.services.gpx import parse_gpx
from app.services.pipeline import Services
from app.services.storage import SURVEY_UPLOADS
from app.services.video import is_mp4, mp4_header

router = APIRouter(tags=["engineer"])


def _out(s: Survey, overlap: bool | None = None) -> SurveyOut:
    return SurveyOut(
        id=s.id,
        name=s.name,
        status=s.status,
        progress=s.progress,
        frames_total=s.frames_total,
        detections_count=s.detections_count,
        defects_new=s.defects_new,
        defects_merged=s.defects_merged,
        error=s.error,
        created_at=s.created_at,
        started_at=s.started_at,
        finished_at=s.finished_at,
        gpx_overlap=overlap,
    )


@router.post("/surveys", response_model=SurveyOut)
async def create_survey(
    name: str = Form(..., min_length=1, max_length=120),
    video: UploadFile = File(...),
    gpx: UploadFile = File(...),
    staff: Staff = Depends(require_engineer),
    db: Session = Depends(get_db),
    services: Services = Depends(get_services),
) -> SurveyOut:
    max_mb = get_settings().max_upload_mb
    video_bytes = await read_limited(video, max_mb)
    if not is_mp4(video_bytes):
        raise ApiError("invalid_image", 415, "The video must be an MP4 file.")
    gpx_bytes = await read_limited(gpx, 5)
    try:
        track = parse_gpx(gpx_bytes.decode("utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001 - any parse error means a bad file
        raise ApiError(
            "survey_gpx_mismatch", 422, "The GPS file is not a valid GPX track."
        ) from exc
    if not track.times:
        raise ApiError("survey_gpx_mismatch", 422, "The GPS track has no timed points.")

    header = mp4_header(video_bytes)
    overlap: bool | None = None
    if header and header.created and header.duration_s:
        overlap = track.overlaps(
            header.created, header.created + timedelta(seconds=header.duration_s)
        )

    survey_id = uuid.uuid4()
    video_path, gpx_path = f"{survey_id}/video.mp4", f"{survey_id}/track.gpx"
    services.storage.upload(SURVEY_UPLOADS, video_path, video_bytes, "video/mp4")
    services.storage.upload(SURVEY_UPLOADS, gpx_path, gpx_bytes, "application/gpx+xml")
    survey = Survey(
        id=survey_id,
        name=name.strip(),
        video_path=video_path,
        gpx_path=gpx_path,
        created_by=staff.id,
        progress=0,
        detections_count=0,
        defects_new=0,
        defects_merged=0,
    )
    db.add(survey)
    db.flush()
    db.refresh(survey)
    return _out(survey, overlap)


@router.get("/surveys", response_model=list[SurveyOut])
def list_surveys(_: Staff = Depends(get_staff), db: Session = Depends(get_db)) -> list[SurveyOut]:
    rows = db.scalars(select(Survey).order_by(Survey.created_at.desc()).limit(100)).all()
    return [_out(s) for s in rows]


@router.get("/surveys/{survey_id}", response_model=SurveyOut)
def get_survey(
    survey_id: uuid.UUID, _: Staff = Depends(get_staff), db: Session = Depends(get_db)
) -> SurveyOut:
    s = db.get(Survey, survey_id)
    if s is None:
        raise ApiError("not_found", 404, "No survey found with this ID.")
    return _out(s)
