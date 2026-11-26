"""RoadSense FastAPI application."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, reports
from app.core.config import get_settings
from app.core.errors import install_error_handlers

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Detects road damage, scores severity, merges reports and ranks repairs.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(reports.router)
    if settings.environment == "development":
        from fastapi.staticfiles import StaticFiles

        from app.services.storage import LOCAL_ROOT

        LOCAL_ROOT.mkdir(exist_ok=True)
        app.mount("/local-storage", StaticFiles(directory=LOCAL_ROOT), name="local-storage")
    return app


app = create_app()
