"""Allowed status changes (docs/backend-schema.md). Anything else is invalid_transition."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Defect, StatusHistory
from app.models.enums import DamageClass, SeverityLabel
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


# Score given to an engineer's own severity label (the middle of each band).
LABEL_SCORE = {
    SeverityLabel.minor: 0.25,
    SeverityLabel.moderate: 0.55,
    SeverityLabel.dangerous: 0.85,
}


def accept_review(
    defect: Defect, damage_class: DamageClass | None, severity_label: SeverityLabel | None
) -> None:
    """A needs-review defect accepted by an engineer gets their damage type and severity,
    so it can be ranked. Without them it keeps no severity (priority 0) until a report scores it.
    """
    if damage_class is not None:
        defect.damage_class = damage_class
    if severity_label is not None and defect.severity_score is None:
        defect.severity_label = severity_label
        defect.severity_score = LABEL_SCORE[severity_label]
