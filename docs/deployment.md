# Deployment (D2, D3)

Frontend on Vercel, backend container on Azure Container Apps, data on Supabase, models on the
Hugging Face Hub. Everything is free-tier. Allow about 2 hours the first time.

Order: **Supabase → GitHub image → Azure → Vercel → connect them → check.**
Keep a private note of every key; never commit or paste keys into chat.

## 0. Before you start

- GitHub Student Developer Pack approved (needed for Azure for Students without a card).
- Install the [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) and
  [uv](https://docs.astral.sh/uv/) on your laptop.

## 1. Supabase (database, storage, auth)

1. [supabase.com](https://supabase.com) → **New project**. Region: **Mumbai (ap-south-1)**.
   Save the database password.
2. **Database → Extensions** → enable **postgis**.
3. **Storage → New bucket**, three times:
   `report-images` (public), `fixed-photos` (public), `survey-uploads` (private).
4. **Project Settings → API Keys**. Note the **Project URL**, the **anon** key and the
   **service_role** key (under *Legacy API keys* if your project shows new-style keys; the backend
   uses the legacy JWT keys).
5. **Project Settings → JWT** (or *JWT Keys*): if a **Legacy JWT secret** is shown, note it. Newer
   projects sign with asymmetric keys, which the backend verifies automatically; then leave
   `SUPABASE_JWT_SECRET` empty.
6. **Connect** button (top bar) → **Session pooler** connection string. It looks like
   `postgresql://postgres.<ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres`.
   Change the start to `postgresql+psycopg://`. This is your `DATABASE_URL`.
   Use the **session** pooler (port 5432): the direct connection is IPv6-only (GitHub Actions and
   Azure can't reach it), and the transaction pooler (6543) breaks the merge locks.
7. Create the tables from your laptop:

```bash
cd backend && uv sync
```

```bash
cd backend && DATABASE_URL='postgresql+psycopg://postgres.<ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres' uv run alembic upgrade head
```

```bash
cd backend && DATABASE_URL='<same as above>' uv run python -m scripts.seed
```

   The seed adds settings version 1. With `data/pilot_area.geojson` in place, add `--fetch-osm`
   to load schools and hospitals.
8. **Authentication → Users → Add user** twice: your engineer account and the demo account
   (`demo@roadsense.app`, a simple password; it is shown on the login screen). Tick
   *Auto confirm user*. Copy each user's **UID**.
9. **SQL Editor** → run, with the two UIDs:

```sql
insert into profiles (id, full_name, role) values
  ('<your-uid>', 'Your Name', 'engineer'),
  ('<demo-uid>', 'Demo user', 'demo');
```

## 2. GitHub: build the backend image

1. Repository **Settings → Environments → New environment** named `production`. Add:

| Kind | Name | Value |
|------|------|-------|
| secret | `DATABASE_URL` | the session-pooler URL from step 1.6 |
| secret | `CRON_SECRET` | a long random string (keep it; Azure needs the same value) |
| secret | `AZURE_CREDENTIALS` | added in step 3.4 |
| variable | `AZURE_CONTAINERAPP_NAME` | `roadsense-api` |
| variable | `AZURE_RESOURCE_GROUP` | `roadsense` |
| variable | `API_URL` | added in step 3.5 |
| variable | `HF_MODEL_REPO` | later, once models exist (bakes them into the image) |

2. Also add `API_URL` and `CRON_SECRET` as **repository** variable/secret (the nightly job reads them).

## 3. Azure Container Apps (backend)

1. Activate **Azure for Students** through the Student Developer Pack, then sign in:

```bash
az login
```

```bash
az extension add --name containerapp --upgrade
```

```bash
az provider register --namespace Microsoft.App && az provider register --namespace Microsoft.OperationalInsights
```

2. Create the resource group and environment:

```bash
az group create --name roadsense --location centralindia
```

```bash
az containerapp env create --name roadsense-env --resource-group roadsense --location centralindia
```

3. Create the app with Microsoft's placeholder image (the deploy workflow swaps in RoadSense):

```bash
az containerapp create --name roadsense-api --resource-group roadsense --environment roadsense-env --image mcr.microsoft.com/k8se/quickstart:latest --target-port 8000 --ingress external --cpu 1 --memory 2Gi --min-replicas 0 --max-replicas 1
```

4. Create the credentials GitHub uses, and paste the JSON output into the `AZURE_CREDENTIALS`
   secret (step 2.1). Get your subscription ID with `az account show --query id -o tsv`.

```bash
az ad sp create-for-rbac --name roadsense-deploy --role contributor --scopes /subscriptions/<subscription-id>/resourceGroups/roadsense --sdk-auth
```

5. Get the API address and put `https://<that address>` into the `API_URL` variables (step 2):

```bash
az containerapp show --name roadsense-api --resource-group roadsense --query properties.configuration.ingress.fqdn -o tsv
```

6. Add the backend's settings. Secrets first, then the environment variables that use them
   (replace every `<...>`):

```bash
az containerapp secret set --name roadsense-api --resource-group roadsense --secrets database-url='<DATABASE_URL>' service-key='<service_role key>' jwt-secret='<legacy JWT secret, or the word unused>' cron-secret='<CRON_SECRET>' ip-salt='<another random string>'
```

```bash
az containerapp update --name roadsense-api --resource-group roadsense --set-env-vars DATABASE_URL=secretref:database-url SUPABASE_SERVICE_KEY=secretref:service-key SUPABASE_JWT_SECRET=secretref:jwt-secret CRON_SECRET=secretref:cron-secret IP_HASH_SALT=secretref:ip-salt SUPABASE_URL=https://<ref>.supabase.co PUBLIC_API_URL=https://<api-address> ALLOWED_ORIGINS=http://localhost:5173 MODEL_VERSION=none-yet PILOT_AREA_NAME="the pilot area"
```

   Azure doesn't accept empty secrets: if your project has no legacy JWT secret (step 1.5), use
   the word `unused`; the backend then verifies tokens with Supabase's public keys.
   `ALLOWED_ORIGINS` gets the Vercel address in step 5. Add `HF_MODEL_REPO=<hf-user>/roadsense-models`
   once models exist.

## 4. Deploy the backend

1. GitHub → **Actions → Deploy backend → Run workflow** (choose your branch). It builds the image,
   pushes it to GitHub Container Registry, runs the migrations and updates the container app.
   After merging to `main`, it runs on every push that changes `backend/`.
2. The first run's "Update the container app" step fails because the image is private. Open your
   GitHub profile → **Packages → roadsense-api → Package settings → Change visibility → Public**,
   then **Re-run failed jobs**.
3. Check: `https://<api-address>/health` returns `{"status":"ok",...}` (the first request after
   idle can take 20–40 s) and `https://<api-address>/docs` shows the API.

## 5. Vercel (frontend)

1. [vercel.com](https://vercel.com) → **Add New → Project** → import the repository.
2. **Root Directory: `frontend`**. Framework: Vite (detected). Leave the build settings alone;
   `vercel.json` sets them.
3. **Environment Variables**:

| Variable | Value |
|----------|-------|
| `VITE_API_URL` | `https://<api-address>` |
| `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | the anon key (public by design; it can only read the public view) |
| `VITE_DEMO_EMAIL` / `VITE_DEMO_PASSWORD` | the demo account from step 1.8 |
| `VITE_PILOT_AREA_NAME` | e.g. `Jayanagar–BTM Layout` |
| `VITE_MAP_CENTER` | `lat,lon` of your route, e.g. `12.9250,77.5938` |

4. **Deploy**. Note the address, e.g. `https://roadsense.vercel.app`.
5. Vercel builds from the branch you pick as the production branch (Settings → Git); set it to
   your working branch until you merge to `main`.

## 6. Connect them

1. Allow the frontend to call the API:

```bash
az containerapp update --name roadsense-api --resource-group roadsense --set-env-vars ALLOWED_ORIGINS=https://<your-app>.vercel.app
```

2. Supabase → **Authentication → URL Configuration** → Site URL `https://<your-app>.vercel.app`.
3. Supabase → **Database → Publications → supabase_realtime**: `defects` should be listed
   (migration 0004 adds it). Live dashboard updates need it.

## 7. Check it works

- [ ] `https://<api-address>/health` is ok
- [ ] The app opens on your phone over mobile data (not just Wi-Fi)
- [ ] **Engineer sign in** works with your account and with **Try the demo account**
- [ ] The dashboard, repair list, analytics and settings screens load
- [ ] GitHub → Actions → **Nightly → Run workflow** succeeds (ticks D3)
- [ ] Photo reports: these need trained models. Until `HF_MODEL_REPO` is set (after the Kaggle
      notebook), submitting a photo shows an error. Everything else works.

## After the models exist

Set the `HF_MODEL_REPO` repository variable and the container app variables `HF_MODEL_REPO` and
`MODEL_VERSION`, run **Deploy backend** again (it bakes the models into the image), and copy
`yolo-nano.onnx` into `frontend/public/models/` for Drive mode (or host it and adjust the URL).

## Before a demo

Open the app 5–10 minutes early: scale-to-zero means the first request loads the models (20–40 s).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Deploy fails at "Run migrations": connection refused or timed out | Use the **session pooler** URL, not the direct one |
| Container app shows "Activation failed" | `az containerapp logs show --name roadsense-api --resource-group roadsense --follow`; usually a missing env var |
| Browser console: CORS error | `ALLOWED_ORIGINS` must exactly match the Vercel address (https, no trailing slash) |
| Sign-in works but screens say "Please sign in again" | The user has no row in `profiles` (step 1.9), or the JWT secret is wrong |
| Map is empty for the public | Normal until there are open defects |
