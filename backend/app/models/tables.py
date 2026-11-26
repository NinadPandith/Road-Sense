import uuid
from datetime import datetime

from geoalchemy2 import Geography
from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Integer,
    SmallInteger,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.enums import (
    DamageClass,
    DefectStatus,
    ReportSource,
    ReportStatus,
    RoadClass,
    SeverityLabel,
    SurveyStatus,
    UserRole,
    pg_enum,
)

POINT = Geography(geometry_type="POINT", srid=4326, spatial_index=False)
MULTIPOLYGON = Geography(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False)


class Base(DeclarativeBase):
    pass


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


class Profile(Base):
    __tablename__ = "profiles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    role: Mapped[UserRole] = mapped_column(
        pg_enum(UserRole, "user_role"), default=UserRole.engineer
    )
    created_at: Mapped[datetime] = _now()


class Ward(Base):
    __tablename__ = "wards"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    boundary: Mapped[object] = mapped_column(MULTIPOLYGON)


class SensitivePlace(Base):
    __tablename__ = "sensitive_places"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    kind: Mapped[str] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    osm_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    location: Mapped[object] = mapped_column(POINT)


class Survey(Base):
    __tablename__ = "surveys"
    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(Text)
    video_path: Mapped[str] = mapped_column(Text)
    gpx_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[SurveyStatus] = mapped_column(
        pg_enum(SurveyStatus, "survey_status"), default=SurveyStatus.queued
    )
    progress: Mapped[int] = mapped_column(SmallInteger, default=0)
    frames_total: Mapped[int | None] = mapped_column(Integer)
    detections_count: Mapped[int] = mapped_column(Integer, default=0)
    defects_new: Mapped[int] = mapped_column(Integer, default=0)
    defects_merged: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("profiles.id"))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()


class Defect(Base):
    __tablename__ = "defects"
    id: Mapped[uuid.UUID] = _uuid_pk()
    location: Mapped[object] = mapped_column(POINT)
    damage_class: Mapped[DamageClass | None] = mapped_column(pg_enum(DamageClass, "damage_class"))
    severity_score: Mapped[float | None] = mapped_column(Float(precision=24))
    severity_label: Mapped[SeverityLabel | None] = mapped_column(
        pg_enum(SeverityLabel, "severity_label")
    )
    report_count: Mapped[int] = mapped_column(Integer, default=1)
    road_class: Mapped[RoadClass] = mapped_column(
        pg_enum(RoadClass, "road_class"), default=RoadClass.unknown
    )
    road_name: Mapped[str | None] = mapped_column(Text)
    osm_way_id: Mapped[int | None] = mapped_column(BigInteger)
    ward_id: Mapped[int | None] = mapped_column(ForeignKey("wards.id"))
    near_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)
    sensitive_place_id: Mapped[int | None] = mapped_column(ForeignKey("sensitive_places.id"))
    priority: Mapped[float] = mapped_column(Float(precision=24), default=0)
    priority_terms: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[DefectStatus] = mapped_column(
        pg_enum(DefectStatus, "defect_status"), default=DefectStatus.reported
    )
    first_reported_at: Mapped[datetime] = _now()
    last_reported_at: Mapped[datetime] = _now()
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fixed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fixed_photo_path: Mapped[str | None] = mapped_column(Text)
    reopened_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[uuid.UUID] = _uuid_pk()
    tracking_code: Mapped[str] = mapped_column(Text, unique=True)
    client_report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), unique=True)
    source: Mapped[ReportSource] = mapped_column(pg_enum(ReportSource, "report_source"))
    status: Mapped[ReportStatus] = mapped_column(
        pg_enum(ReportStatus, "report_status"), default=ReportStatus.processing
    )
    survey_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("surveys.id"))
    defect_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("defects.id"))
    image_path: Mapped[str | None] = mapped_column(Text)
    thumb_path: Mapped[str | None] = mapped_column(Text)
    location: Mapped[object] = mapped_column(POINT)
    gps_accuracy_m: Mapped[float | None] = mapped_column(Float(precision=24))
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    ip_hash: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = _now()


class Detection(Base):
    __tablename__ = "detections"
    id: Mapped[uuid.UUID] = _uuid_pk()
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"))
    damage_class: Mapped[DamageClass] = mapped_column(pg_enum(DamageClass, "damage_class"))
    confidence: Mapped[float] = mapped_column(Float(precision=24))
    box: Mapped[list[float]] = mapped_column(ARRAY(Float(precision=24)))
    size_score: Mapped[float] = mapped_column(Float(precision=24))
    depth_score: Mapped[float | None] = mapped_column(Float(precision=24))
    type_score: Mapped[float] = mapped_column(Float(precision=24))
    position_score: Mapped[float] = mapped_column(Float(precision=24))
    severity_score: Mapped[float] = mapped_column(Float(precision=24))
    severity_label: Mapped[SeverityLabel] = mapped_column(pg_enum(SeverityLabel, "severity_label"))
    model_version: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()


class StatusHistory(Base):
    __tablename__ = "status_history"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    defect_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("defects.id", ondelete="CASCADE"))
    from_status: Mapped[DefectStatus | None] = mapped_column(pg_enum(DefectStatus, "defect_status"))
    to_status: Mapped[DefectStatus] = mapped_column(pg_enum(DefectStatus, "defect_status"))
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = _now()


class SettingsVersion(Base):
    __tablename__ = "settings_versions"
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    values: Mapped[dict] = mapped_column(JSONB)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("profiles.id"))
    created_at: Mapped[datetime] = _now()
