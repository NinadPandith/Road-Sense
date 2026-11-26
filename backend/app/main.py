"""RoadSense FastAPI application."""

import logging
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, reports, staff, surveys
from app.core.config import get_settings
from app.core.errors import install_error_handlers

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _warm_up() -> None:
    """Load the models in the background so the first report after a cold start is fast."""
    from app.services.depth import get_depth_estimator
    from app.services.detect import get_detector

    try:
        get_detector()
        get_depth_estimator()
        log.info("Models loaded")
    except Exception as exc:  # noqa: BLE001 - the API still serves tracking and staff pages
        log.warning("Model warm-up failed: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    worker = None
    if settings.environment == "production":
        threading.Thread(target=_warm_up, daemon=True).start()
    if settings.survey_worker_enabled:
        from app.api.deps import default_services
        from app.core.db import get_sessionmaker
        from app.services.surveys import SurveyWorker, committing

        worker = SurveyWorker(lambda: committing(get_sessionmaker()), default_services())
        worker.start()
    yield
    if worker:
        worker.stop()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Detects road damage, scores severity, merges reports and ranks repairs.",
        lifespan=lifespan,
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
    app.include_router(staff.router)
    app.include_router(surveys.router)
    if settings.environment == "development":
        from fastapi.staticfiles import StaticFiles

        from app.services.storage import LOCAL_ROOT

        LOCAL_ROOT.mkdir(exist_ok=True)
        app.mount("/local-storage", StaticFiles(directory=LOCAL_ROOT), name="local-storage")
    return app


app = create_app()
