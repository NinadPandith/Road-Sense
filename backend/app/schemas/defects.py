"""Staff response shapes (docs/backend-schema.md: DefectListItem, DefectDetail, Stats)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import DamageClass, DefectStatus, ReportSource, RoadClass, SeverityLabel
from app.schemas.reports import BoxOut


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


class WardOut(BaseModel):
    id: int
    name: str


class DefectListItem(BaseModel):
    id: uuid.UUID
    rank: int | None
    lat: float
    lon: float
    damage_class: DamageClass | None
    severity_label: SeverityLabel | None
    severity_score: float | None
    priority: float
    priority_reason: str
    road_class: RoadClass
    road_name: str | None
    ward: WardOut | None
    report_count: int
    age_days: int
    status: DefectStatus
    near_sensitive: bool
    first_reported_at: datetime
    thumb_url: str | None


class DetectionOut(BoxOut):
    size_score: float
    depth_score: float | None
    type_score: float
    position_score: float
    severity_score: float
    severity_label: SeverityLabel


class ReportOut(BaseModel):
    id: uuid.UUID
    tracking_code: str
    source: ReportSource
    lat: float
    lon: float
    image_url: str | None
    note: str | None
    detections: list[DetectionOut]
    created_at: datetime


class HistoryOut(BaseModel):
    from_status: DefectStatus | None
    to_status: DefectStatus
    changed_by: str | None
    reason: str | None
    created_at: datetime


class DefectDetail(DefectListItem):
    priority_terms: dict
    sensitive_place: str | None
    reopened_count: int
    fixed_at: datetime | None
    fixed_photo_url: str | None
    reports: list[ReportOut]
    history: list[HistoryOut]
    merge_radius_m: float


class BulkStatusIn(BaseModel):
    ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    to_status: DefectStatus
    reason: str | None = Field(None, max_length=200)


class BulkStatusOut(BaseModel):
    updated: int
    skipped: list[uuid.UUID] = []


class CountItem(BaseModel):
    key: str
    count: int


class WeekItem(BaseModel):
    week_start: str
    fixed: int
    reported: int


class Stats(BaseModel):
    open_defects: int
    dangerous_open: int
    new_this_week: int
    fixed_this_week: int
    needs_review: int
    open_by_severity: list[CountItem]
    open_by_ward: list[CountItem]
    per_week: list[WeekItem]


class Updated(BaseModel):
    updated: int
