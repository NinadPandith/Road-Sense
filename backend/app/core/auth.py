"""Engineer authentication: verify the Supabase Auth JWT sent by the frontend.

Supports both legacy HS256 projects (SUPABASE_JWT_SECRET) and newer asymmetric keys (JWKS).
The demo role is enforced here: every write endpoint depends on `require_engineer`.
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.errors import ApiError
from app.models import Profile
from app.models.enums import UserRole


@dataclass(frozen=True)
class Staff:
    id: uuid.UUID
    role: UserRole
    full_name: str

    @property
    def is_engineer(self) -> bool:
        return self.role == UserRole.engineer


@lru_cache
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_keys=True)


def decode_token(token: str) -> dict:
    s = get_settings()
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "HS256":
            if not s.supabase_jwt_secret:
                raise ApiError("unauthorized", 401)
            key: object = s.supabase_jwt_secret
        else:
            jwks = f"{s.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
            key = _jwks_client(jwks).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            key,  # type: ignore[arg-type]
            algorithms=["HS256", "RS256", "ES256"],
            audience="authenticated",
        )
    except jwt.PyJWTError as exc:
        raise ApiError("unauthorized", 401) from exc


def get_staff(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> Staff:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError("unauthorized", 401)
    claims = decode_token(authorization.split(" ", 1)[1])
    try:
        user_id = uuid.UUID(claims["sub"])
    except (KeyError, ValueError) as exc:
        raise ApiError("unauthorized", 401) from exc
    profile = db.get(Profile, user_id)
    if profile is None:
        raise ApiError("unauthorized", 401, "This account has no RoadSense access.")
    return Staff(id=profile.id, role=profile.role, full_name=profile.full_name)


def require_engineer(staff: Staff = Depends(get_staff)) -> Staff:
    if not staff.is_engineer:
        raise ApiError("forbidden_demo", 403)
    return staff


def require_cron(x_cron_secret: str | None = Header(None)) -> None:
    if not x_cron_secret or x_cron_secret != get_settings().cron_secret:
        raise ApiError("unauthorized", 401)
