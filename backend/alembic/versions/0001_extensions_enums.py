"""Extensions and the 8 enum types.

Revision ID: 0001
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

ENUMS = {
    "report_source": ["citizen", "drive", "survey"],
    "report_status": ["processing", "done", "no_damage", "needs_review", "failed"],
    "damage_class": ["pothole", "alligator_crack", "crack_across", "crack_along"],
    "severity_label": ["minor", "moderate", "dangerous"],
    "defect_status": ["needs_review", "reported", "verified", "assigned", "fixed", "rejected"],
    "survey_status": [
        "queued", "extracting", "detecting", "scoring", "merging", "done", "failed",
    ],
    "road_class": ["major", "secondary", "tertiary", "residential", "unknown"],
    "user_role": ["engineer", "demo"],
}


def upgrade() -> None:
    op.execute("create extension if not exists postgis")
    op.execute("create extension if not exists pgcrypto")
    for name, values in ENUMS.items():
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(f"create type {name} as enum ({vals})")


def downgrade() -> None:
    for name in reversed(ENUMS):
        op.execute(f"drop type if exists {name}")
