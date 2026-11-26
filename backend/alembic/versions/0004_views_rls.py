"""public_defects view, Row Level Security, grants and realtime publication.

Revision ID: 0004
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

STAFF_TABLES = ["reports", "detections", "defects", "status_history", "surveys", "settings_versions"]
PUBLIC_LOOKUPS = ["wards", "sensitive_places"]

VIEW = r"""
create view public_defects with (security_invoker = false) as
select d.id,
       ST_Y(d.location::geometry) as lat,
       ST_X(d.location::geometry) as lon,
       d.damage_class, d.severity_label, d.status, d.report_count,
       d.first_reported_at, d.fixed_at,
       (select r.thumb_path from reports r
         where r.defect_id = d.id and r.thumb_path is not null
         order by r.created_at desc limit 1) as thumb_path
from defects d
where d.status in ('reported', 'verified', 'assigned')
   or (d.status = 'fixed' and d.fixed_at > now() - interval '30 days');
grant select on public_defects to anon, authenticated;
"""


def upgrade() -> None:
    op.execute(VIEW)
    for t in STAFF_TABLES:
        op.execute(f"alter table {t} enable row level security")
        op.execute(
            f"create policy staff_read on {t} for select to authenticated "
            "using (exists (select 1 from profiles p where p.id = auth.uid()))"
        )
        op.execute(f"grant select on {t} to authenticated")
    op.execute("alter table profiles enable row level security")
    op.execute(
        "create policy own_row on profiles for select to authenticated using (id = auth.uid())"
    )
    op.execute("grant select on profiles to authenticated")
    for t in PUBLIC_LOOKUPS:
        op.execute(f"alter table {t} enable row level security")
        op.execute(f"create policy public_read on {t} for select to anon, authenticated using (true)")
        op.execute(f"grant select on {t} to anon, authenticated")
    # Realtime: dashboard subscribes to defects (Supabase creates this publication).
    op.execute(
        """
        do $$ begin
          if exists (select 1 from pg_publication where pubname = 'supabase_realtime') then
            alter publication supabase_realtime add table defects;
          end if;
        end $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        do $$ begin
          if exists (select 1 from pg_publication_tables
                     where pubname = 'supabase_realtime' and tablename = 'defects') then
            alter publication supabase_realtime drop table defects;
          end if;
        end $$;
        """
    )
    for t in PUBLIC_LOOKUPS:
        op.execute(f"drop policy if exists public_read on {t}")
        op.execute(f"alter table {t} disable row level security")
    op.execute("drop policy if exists own_row on profiles")
    op.execute("alter table profiles disable row level security")
    for t in STAFF_TABLES:
        op.execute(f"drop policy if exists staff_read on {t}")
        op.execute(f"alter table {t} disable row level security")
    op.execute("drop view if exists public_defects")
