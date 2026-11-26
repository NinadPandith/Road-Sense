"""Response shapes for citizen endpoints (docs/backend-schema.md, "API schemas")."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.models.enums import DamageClass, DefectStatus, ReportStatus, SeverityLabel

Outcome = Literal["new", "merged", "no_damage", "needs_review", "processing"]
ConfidenceLabel = Literal["very_likely", "likely", "possible"]


class SeverityFactors(BaseModel):
    size: float
    depth: float | None
    type: float
    position: float


class Severity(BaseModel):
    label: SeverityLabel
    score: float
    factors: SeverityFactors
    reason: str


class BoxOut(BaseModel):
    damage_class: DamageClass
    confidence: float
    box: list[float]


class ReportResult(BaseModel):
    tracking_code: str
    status: ReportStatus
    outcome: Outcome
    defect_id: uuid.UUID | None = None
    report_count: int | None = None
    damage_class: DamageClass | None = None
    confidence_label: ConfidenceLabel | None = None
    severity: Severity | None = None
    boxes: list[BoxOut] = []
    thumb_url: str | None = None
    image_url: str | None = None


class TimelineStep(BaseModel):
    status: DefectStatus
    at: datetime | None


class TrackResult(BaseModel):
    tracking_code: str
    report_status: ReportStatus
    created_at: datetime
    defect_status: DefectStatus | None = None
    damage_class: DamageClass | None = None
    severity_label: SeverityLabel | None = None
    report_count: int | None = None
    image_url: str | None = None
    thumb_url: str | None = None
    fixed_photo_url: str | None = None
    timeline: list[TimelineStep] = []
