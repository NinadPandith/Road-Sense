"""Shared FastAPI dependencies."""

from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.services import geo
from app.services.depth import get_depth_estimator
from app.services.detect import get_detector
from app.services.pipeline import Services, hash_ip
from app.services.settings import SettingsValues, load_active
from app.services.storage import make_storage


@lru_cache
def default_services() -> Services:
    return Services(
        get_detector=get_detector,
        get_depth=get_depth_estimator,
        storage=make_storage(),
        road_lookup=geo.lookup_road,
        model_version=get_settings().model_version,
    )


def get_services() -> Services:
    return default_services()


def get_scoring_settings(db: Session = Depends(get_db)) -> SettingsValues:
    return load_active(db)


def client_ip(request: Request) -> str:
    """Azure Container Apps and Vercel put the real client first in X-Forwarded-For."""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_ip_hash(request: Request) -> str:
    return hash_ip(client_ip(request), get_settings().ip_hash_salt)
