"""Indexes and updated_at triggers.

Revision ID: 0003
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

SQL = r"""
create index defects_location_gix on defects using gist (location);
create index reports_location_gix on reports using gist (location);
create index sensitive_places_location_gix on sensitive_places using gist (location);
create index wards_boundary_gix on wards using gist (boundary);

create index defects_status_priority_idx on defects (status, priority desc);
create index defects_ward_idx on defects (ward_id);

create index reports_defect_idx on reports (defect_id);
create index reports_survey_idx on reports (survey_id);
create index reports_iphash_time on reports (ip_hash, created_at desc);
create index detections_report_idx on detections (report_id);
create index status_history_defect on status_history (defect_id, created_at desc);
create index surveys_status_idx on surveys (status) where status not in ('done', 'failed');

create or replace function set_updated_at() returns trigger as $$
begin new.updated_at = now(); return new; end; $$ language plpgsql;

create trigger defects_updated_at before update on defects
  for each row execute function set_updated_at();
create trigger reports_updated_at before update on reports
  for each row execute function set_updated_at();
create trigger surveys_updated_at before update on surveys
  for each row execute function set_updated_at();
"""


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    for t in ("defects", "reports", "surveys"):
        op.execute(f"drop trigger if exists {t}_updated_at on {t}")
    op.execute("drop function if exists set_updated_at()")
    for i in (
        "defects_location_gix", "reports_location_gix", "sensitive_places_location_gix",
        "wards_boundary_gix", "defects_status_priority_idx", "defects_ward_idx",
        "reports_defect_idx", "reports_survey_idx", "reports_iphash_time",
        "detections_report_idx", "status_history_defect", "surveys_status_idx",
    ):
        op.execute(f"drop index if exists {i}")
