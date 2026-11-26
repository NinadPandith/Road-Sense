"""Core tables (docs/backend-schema.md, "Tables").

Revision ID: 0002
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SQL = r"""
create table profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text not null,
  role user_role not null default 'engineer',
  created_at timestamptz not null default now()
);

create table wards (
  id bigint generated always as identity primary key,
  code text unique not null,
  name text not null,
  boundary geography(MultiPolygon, 4326) not null
);

create table sensitive_places (
  id bigint generated always as identity primary key,
  kind text not null check (kind in ('school', 'hospital')),
  name text,
  osm_id bigint unique,
  location geography(Point, 4326) not null
);

create table surveys (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  video_path text not null,
  gpx_path text,
  status survey_status not null default 'queued',
  progress smallint not null default 0 check (progress between 0 and 100),
  frames_total int,
  detections_count int not null default 0,
  defects_new int not null default 0,
  defects_merged int not null default 0,
  error text,
  created_by uuid not null references profiles(id),
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table defects (
  id uuid primary key default gen_random_uuid(),
  location geography(Point, 4326) not null,
  damage_class damage_class,
  severity_score real check (severity_score between 0 and 1),
  severity_label severity_label,
  report_count int not null default 1 check (report_count >= 1),
  road_class road_class not null default 'unknown',
  road_name text,
  osm_way_id bigint,
  ward_id bigint references wards(id),
  near_sensitive boolean not null default false,
  sensitive_place_id bigint references sensitive_places(id),
  priority real not null default 0,
  priority_terms jsonb not null default '{}',
  status defect_status not null default 'reported',
  first_reported_at timestamptz not null default now(),
  last_reported_at timestamptz not null default now(),
  verified_at timestamptz,
  assigned_at timestamptz,
  fixed_at timestamptz,
  fixed_photo_path text,
  reopened_count int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table reports (
  id uuid primary key default gen_random_uuid(),
  tracking_code text unique not null check (tracking_code ~ '^RS-[2-9A-HJKMNP-Z]{4,6}$'),
  client_report_id uuid unique,
  source report_source not null,
  status report_status not null default 'processing',
  survey_id uuid references surveys(id) on delete set null,
  defect_id uuid references defects(id),
  image_path text,
  thumb_path text,
  location geography(Point, 4326) not null,
  gps_accuracy_m real,
  captured_at timestamptz not null,
  note text check (char_length(note) <= 200),
  ip_hash text,
  model_version text,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table detections (
  id uuid primary key default gen_random_uuid(),
  report_id uuid not null references reports(id) on delete cascade,
  damage_class damage_class not null,
  confidence real not null check (confidence between 0 and 1),
  box real[4] not null,
  size_score real not null check (size_score between 0 and 1),
  depth_score real check (depth_score between 0 and 1),
  type_score real not null check (type_score between 0 and 1),
  position_score real not null check (position_score between 0 and 1),
  severity_score real not null check (severity_score between 0 and 1),
  severity_label severity_label not null,
  model_version text not null,
  created_at timestamptz not null default now()
);

create table status_history (
  id bigint generated always as identity primary key,
  defect_id uuid not null references defects(id) on delete cascade,
  from_status defect_status,
  to_status defect_status not null,
  changed_by uuid references profiles(id),
  reason text,
  created_at timestamptz not null default now()
);

create table settings_versions (
  id bigint generated always as identity primary key,
  values jsonb not null,
  created_by uuid references profiles(id),
  created_at timestamptz not null default now()
);
"""

TABLES = [
    "settings_versions", "status_history", "detections", "reports", "defects",
    "surveys", "sensitive_places", "wards", "profiles",
]


def upgrade() -> None:
    op.execute(SQL)


def downgrade() -> None:
    for t in TABLES:
        op.execute(f"drop table if exists {t} cascade")
