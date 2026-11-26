"""Postgres enum types (migration 0001). Python values equal the database values."""

import enum

from sqlalchemy import Enum as SAEnum


class ReportSource(enum.StrEnum):
    citizen = "citizen"
    drive = "drive"
    survey = "survey"


class ReportStatus(enum.StrEnum):
    processing = "processing"
    done = "done"
    no_damage = "no_damage"
    needs_review = "needs_review"
    failed = "failed"


class DamageClass(enum.StrEnum):
    pothole = "pothole"
    alligator_crack = "alligator_crack"
    crack_across = "crack_across"
    crack_along = "crack_along"


class SeverityLabel(enum.StrEnum):
    minor = "minor"
    moderate = "moderate"
    dangerous = "dangerous"


class DefectStatus(enum.StrEnum):
    needs_review = "needs_review"
    reported = "reported"
    verified = "verified"
    assigned = "assigned"
    fixed = "fixed"
    rejected = "rejected"


OPEN_STATUSES = (
    DefectStatus.needs_review,
    DefectStatus.reported,
    DefectStatus.verified,
    DefectStatus.assigned,
)


class SurveyStatus(enum.StrEnum):
    queued = "queued"
    extracting = "extracting"
    detecting = "detecting"
    scoring = "scoring"
    merging = "merging"
    done = "done"
    failed = "failed"


class RoadClass(enum.StrEnum):
    major = "major"
    secondary = "secondary"
    tertiary = "tertiary"
    residential = "residential"
    unknown = "unknown"


class UserRole(enum.StrEnum):
    engineer = "engineer"
    demo = "demo"


def pg_enum(py_enum: type[enum.Enum], name: str) -> SAEnum:
    """Map to an existing Postgres enum created by migrations (never auto-created)."""
    return SAEnum(
        py_enum,
        name=name,
        create_type=False,
        native_enum=True,
        values_callable=lambda e: [m.value for m in e],
    )
