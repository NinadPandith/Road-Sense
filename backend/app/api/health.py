from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import get_settings

router = APIRouter(tags=["health"])


class Health(BaseModel):
    status: str
    model_version: str


@router.get("/health", response_model=Health)
def health() -> Health:
    return Health(status="ok", model_version=get_settings().model_version)
