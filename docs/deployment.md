# Deployment (D2, D3)

Frontend on Vercel, backend container on Azure Container Apps, data on Supabase, models on the
Hugging Face Hub. Everything below is free-tier.

## 1. Supabase

1. Create the project (region Mumbai, ap-south-1) and enable PostGIS (Database → Extensions).
2. Create the storage buckets: `report-images` (public), `fixed-photos` (public),
   `survey-uploads` (private).
3. Copy the connection string (Settings → Database → Connection string → URI, **session pooler**)
   into `DATABASE_URL`, changing the scheme to `postgresql+psycopg://`.
4. Run the migrations and the seed from your laptop:

```bash
cd backend && uv run alembic upgrade head
```

```bash
cd backend && ENGINEER_EMAIL=you@example.com ENGINEER_PASSWORD=change-me DEMO_EMAIL=demo@roadsense.app DEMO_PASSWORD=roadsense-demo uv run python -m scripts.seed --fetch-osm --users
```

## 2. Backend on Azure Container Apps

```bash
az group create --name roadsense --location centralindia
```

```bash
az containerapp env create --name roadsense-env --resource-group roadsense --location centralindia
```

```bash
az containerapp create --name roadsense-api --resource-group roadsense --environment roadsense-env --image ghcr.io/<github-user>/roadsense-api:latest --target-port 8000 --ingress external --cpu 1 --memory 2Gi --min-replicas 0 --max-replicas 1
```

Then set the environment variables on the container app (portal → Containers → Environment
variables; store secrets as *secrets* and reference them):

| Variable | Value |
|----------|-------|
| `ENVIRONMENT` | `production` |
| `DATABASE_URL` | Supabase connection string (secret) |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | Service role key (secret, backend only) |
| `SUPABASE_JWT_SECRET` | JWT secret (secret; only needed for legacy HS256 projects) |
| `HF_MODEL_REPO` | `<hf-user>/roadsense-models` |
| `MODEL_VERSION` | e.g. `v1-rdd2022` (stored with every detection) |
| `ALLOWED_ORIGINS` | `https://<your-app>.vercel.app` (comma-separated if several) |
| `PUBLIC_API_URL` | `https://<api-host>` |
| `CRON_SECRET` | random string (secret) |
| `IP_HASH_SALT` | random string (secret) |
| `PILOT_AREA_PATH`, `PILOT_AREA_NAME` | path to `pilot_area.geojson` in the image, and its display name |

The GHCR package must be public (or add registry credentials) so Azure can pull it.

GitHub repository settings for `.github/workflows/deploy.yml` (environment `production`):

| Kind | Name | Value |
|------|------|-------|
| secret | `AZURE_CREDENTIALS` | output of `az ad sp create-for-rbac --sdk-auth --role contributor --scopes /subscriptions/<id>/resourceGroups/roadsense` |
| secret | `DATABASE_URL` | Supabase connection string (for migrations) |
| secret | `CRON_SECRET` | same value as the backend's `CRON_SECRET` |
| variable | `AZURE_CONTAINERAPP_NAME` | `roadsense-api` |
| variable | `AZURE_RESOURCE_GROUP` | `roadsense` |
| variable | `API_URL` | `https://<api-host>` |
| variable | `HF_MODEL_REPO` | `<hf-user>/roadsense-models` (bakes models into the image) |

Fallback if Azure activation fails: Modal (see the Tech Stack doc).

## 3. Frontend on Vercel

Import the repo in Vercel, set **Root directory** to `frontend`, and add these environment
variables:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://<api-host>` |
| `VITE_SUPABASE_URL` | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key (public; read-only views only) |
| `VITE_PILOT_AREA_NAME` | e.g. `Jayanagar–BTM Layout` |
| `VITE_MAP_CENTER` | `lat,lon` of the pilot area |
| `VITE_DEMO_EMAIL`, `VITE_DEMO_PASSWORD` | the read-only demo account |

## 4. Nightly job (D3)

`.github/workflows/nightly.yml` runs daily at 02:07 IST. It calls `POST /admin/recalculate`
(priorities grow with age; IP hashes older than 30 days are cleared), which also keeps the free
Supabase project from pausing. Run it once by hand from the Actions tab to tick D3.

## Before a demo

Open the app 5–10 minutes early: scale-to-zero means the first request loads the models (20–40 s).
