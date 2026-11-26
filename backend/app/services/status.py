"""Allowed status changes (docs/backend-schema.md). Anything else is invalid_transition."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Defect, StatusHistory
from app.models.enums import DefectStatus as S

ALLOWED: dict[S, set[S]] = {
    S.needs_review: {S.reported, S.rejected},
    S.reported: {S.verified, S.assigned, S.rejected},
    S.verified: {S.assigned, S.rejected},
    S.assigned: {S.fixed, S.rejected},
    S.fixed: set(),  # fixed -> reported happens only through a new report (system re-open)
    S.rejected: set(),
}


def can_transition(frm: S, to: S) -> bool:
    return to in ALLOWED[frm]


def change_status(
    db: Session,
    defect: Defect,
    to: S,
    changed_by: uuid.UUID | None,
    reason: str | None = None,
    fixed_photo_path: str | None = None,
) -> None:
    if not can_transition(defect.status, to):
        raise ApiError(
            "invalid_transition",
            409,
            f"A defect can't go from {defect.status.value} to {to.value}.",
        )
    now = datetime.now(UTC)
    db.add(
        StatusHistory(
            defect_id=defect.id,
            from_status=defect.status,
            to_status=to,
            changed_by=changed_by,
            reason=reason,
        )
    )
    defect.status = to
    if to == S.verified:
        defect.verified_at = now
    elif to == S.assigned:
        defect.assigned_at = now
    elif to == S.fixed:
        defect.fixed_at = now
        defect.fixed_photo_path = fixed_photo_path
