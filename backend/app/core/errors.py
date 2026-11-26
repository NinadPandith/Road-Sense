"""One error shape for every 4xx/5xx response (Backend Schema, "Error shape").

{"error": {"code": "rate_limited", "message": "...", "retry_after_s": 3600}}
"""

import logging
from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger(__name__)

ErrorCode = Literal[
    "invalid_image",
    "image_too_dark",
    "outside_pilot_area",
    "rate_limited",
    "not_found",
    "forbidden_demo",
    "invalid_transition",
    "survey_gpx_mismatch",
    "unauthorized",
    "validation_error",
    "internal",
]

DEFAULT_MESSAGES: dict[str, str] = {
    "invalid_image": "This file is not a photo we can read. Choose a JPEG, PNG or WebP image.",
    "image_too_dark": "This photo is too dark or blurry to check.",
    "outside_pilot_area": "RoadSense works only in the pilot area right now.",
    "rate_limited": "Too many reports from this network. Please try again in an hour.",
    "not_found": "No report found with this code. Check it and try again.",
    "forbidden_demo": "The demo account is read only.",
    "invalid_transition": "This status change is not allowed.",
    "survey_gpx_mismatch": "GPS track doesn't cover this video's time; points will be unplaced.",
    "unauthorized": "Please sign in again to continue.",
    "validation_error": "Some details are missing or not valid.",
    "internal": "Something went wrong on our side. Please try again.",
}


class ApiError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        status_code: int,
        message: str | None = None,
        retry_after_s: int | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        self.message = message or DEFAULT_MESSAGES[code]
        self.retry_after_s = retry_after_s
        super().__init__(self.message)


def error_body(code: str, message: str, retry_after_s: int | None = None) -> dict:
    err: dict = {"code": code, "message": message}
    if retry_after_s is not None:
        err["retry_after_s"] = retry_after_s
    return {"error": err}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError) -> JSONResponse:
        headers = {"Retry-After": str(exc.retry_after_s)} if exc.retry_after_s else None
        return JSONResponse(
            error_body(exc.code, exc.message, exc.retry_after_s),
            status_code=exc.status_code,
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(p) for p in first.get("loc", [])[1:])
        msg = DEFAULT_MESSAGES["validation_error"]
        if field:
            msg = f"{msg} ({field})"
        return JSONResponse(error_body("validation_error", msg), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {401: "unauthorized", 403: "forbidden_demo", 404: "not_found"}.get(
            exc.status_code, "internal"
        )
        message = exc.detail if isinstance(exc.detail, str) else DEFAULT_MESSAGES[code]
        return JSONResponse(error_body(code, message), status_code=exc.status_code)

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("Unhandled error", exc_info=exc)
        return JSONResponse(error_body("internal", DEFAULT_MESSAGES["internal"]), status_code=500)
