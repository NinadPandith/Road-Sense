import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.enums import SurveyStatus


class SurveyOut(BaseModel):
    id: uuid.UUID
    name: str
    status: SurveyStatus
    progress: int
    frames_total: int | None
    detections_count: int
    defects_new: int
    defects_merged: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    # Only on upload: False when the GPS track doesn't cover the video's time (App Flow, Flow 4).
    gpx_overlap: bool | None = None
