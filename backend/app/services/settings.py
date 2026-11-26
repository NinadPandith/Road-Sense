"""Scoring settings: weights and thresholds. The newest settings_versions row is active.

Defaults are settings v1 from docs/backend-schema.md ("Seed data").
"""

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SettingsVersion


class SeverityWeights(BaseModel):
    A: float = 0.35
    D: float = 0.35
    T: float = 0.20
    P: float = 0.10


class Thresholds(BaseModel):
    moderate: float = 0.40
    dangerous: float = 0.70


class SettingsValues(BaseModel):
    severity_weights: SeverityWeights = Field(default_factory=SeverityWeights)
    thresholds: Thresholds = Field(default_factory=Thresholds)
    type_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "pothole": 1.0,
            "alligator_crack": 0.7,
            "crack_across": 0.5,
            "crack_along": 0.4,
        }
    )
    road_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "major": 1.0,
            "secondary": 0.8,
            "tertiary": 0.6,
            "residential": 0.4,
            "unknown": 0.5,
        }
    )
    merge_radius_m: float = Field(5, gt=0, le=50)
    min_confidence: float = Field(0.35, ge=0, le=1)
    sensitive_radius_m: float = Field(200, gt=0, le=2000)
    sensitive_boost: float = Field(1.3, ge=1, le=3)
    auto_verify_reports: int = Field(3, ge=2, le=50)
    reopen_days: int = Field(30, ge=0, le=365)


DEFAULT_SETTINGS = SettingsValues()


def load_active(db: Session) -> SettingsValues:
    row = db.scalars(select(SettingsVersion).order_by(SettingsVersion.id.desc()).limit(1)).first()
    if row is None:
        return DEFAULT_SETTINGS
    return SettingsValues.model_validate(row.values)
