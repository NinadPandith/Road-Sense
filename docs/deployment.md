# Deployment (D2, D3)

Frontend on Vercel, backend container on Azure Container Apps, data on Supabase, models on the
Hugging Face Hub. Everything is free-tier. **No software to install on your laptop**: the database
setup and the backend deploy run in GitHub Actions, and Azure is set up from Azure Cloud Shell in
the browser.

All keys live in **one place**: GitHub → repository **Settings → Environments → `production`**.
Never paste keys into chats, issues or code.

## 1. Supabase (in the browser)

1. New project, region **South Asia (Mumbai)**, strong database password (letters and numbers is
   easiest). Data access: keep *Enable Data API*, untick *Grant API access to new tables
   automatically*, tick *Enable RLS on new tables automatically*.
2. **Database → Extensions** → switch on **postgis**.
3. **Storage → New bucket**: `report-images` (public), `fixed-photos` (public), `survey-uploads`
   (private).
4. Collect these (Project Settings):
   - **Project URL**: `https://<ref>.supabase.co`
   - **API Keys → Legacy API keys**: `anon` and `service_role`
   - **JWT Keys**: the *Legacy JWT secret* if shown
5. **Connect** (top bar) → **Session pooler** connection string (port **5432**). Put your password
   in place of `[YOUR-PASSWORD]` and change the start to `postgresql+psycopg://`. This is
   `DATABASE_URL`. Special characters in the password must be encoded (`@`→`%40`, `#`→`%23`,
   `/`→`%2F`, `:`→`%3A`, `?`→`%3F`, `%`→`%25`, `&`→`%26`).

## 2. GitHub: the `production` environment

Repository → **Settings → Environments → New environment** → name it `production`. Add:

**Environment secrets**

| Name | Value |
|------|-------|
| `DATABASE_URL` | from step 1.5 |
| `SUPABASE_SERVICE_KEY` | the legacy `service_role` key |
| `SUPABASE_JWT_SECRET` | the legacy JWT secret (leave out if your project has none) |
| `CRON_SECRET` | a long random string |
| `IP_HASH_SALT` | another long random string |
| `ENGINEER_EMAIL` | your email (your engineer login) |
| `ENGINEER_PASSWORD` | your engineer password |
| `DEMO_PASSWORD` | a simple password for the public demo account, e.g. `roadsense-demo` |

**Environment variables**

| Name | Value |
|------|-------|
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `DEMO_EMAIL` | `demo@roadsense.app` (optional; this is the default) |
| `AZURE_CONTAINERAPP_NAME` | `roadsense-api` |
| `AZURE_RESOURCE_GROUP` | `roadsense` |

Random strings, in Windows PowerShell:

```powershell
$b = New-Object byte[] 24; [Security.Cryptography.RNGCryptoServiceProvider]::new().GetBytes($b); ($b | ForEach-Object { $_.ToString('x2') }) -join ''
```

## 3. Set up the database (one click)

GitHub → **Actions → Set up database → Run workflow** (pick branch `claude/eloquent-gates-een41c`
until it's merged to `main`). It checks the secrets, creates the tables, adds the default settings
and creates the engineer and demo users. The run summary lists what it did. Safe to run again.

## 4. Azure (in the browser, about 10 minutes)

1. Activate **Azure for Students** through the GitHub Student Developer Pack (no card needed).
2. Open [portal.azure.com](https://portal.azure.com) → the **>_** (Cloud Shell) icon in the top
   bar → **Bash**. If asked, create the storage it offers ("Mount storage account" / "No storage
   account required" both work).
3. Paste and press Enter:

```bash
curl -fsSL https://raw.githubusercontent.com/NinadPandith/Road-Sense/claude/eloquent-gates-een41c/scripts/azure-setup.sh | bash
```

4. At the end it prints four values. Add them as **variables** in the GitHub `production`
   environment: `API_URL`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.
   They are IDs, not passwords. GitHub signs in to Azure with OIDC, so no Azure password is stored.

## 5. Deploy the backend (one click)

1. GitHub → **Actions → Deploy backend → Run workflow** (same branch). It builds the image, runs
   the migrations, and configures and updates the Azure app from the `production` environment.
2. The first run fails at the smoke test because the new image is private. Open your GitHub
   profile → **Packages → roadsense-api → Package settings → Danger zone → Change visibility →
   Public**, then **Re-run failed jobs**.
3. Open `<API_URL>/health`; it should say `"status":"ok"` (the first request after idle can take
   20–40 s).

## 6. Vercel (in the browser)

1. [vercel.com](https://vercel.com) → sign in with GitHub → **Add New → Project** → import
   `Road-Sense`.
2. **Root Directory: `frontend`**. Leave the build settings alone (`vercel.json` sets them).
3. **Environment Variables**:

| Name | Value |
|------|-------|
| `VITE_API_URL` | your `API_URL` |
| `VITE_SUPABASE_URL` | `https://<ref>.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | the legacy `anon` key (public by design) |
| `VITE_DEMO_EMAIL` | `demo@roadsense.app` |
| `VITE_DEMO_PASSWORD` | the same as `DEMO_PASSWORD` (it's shown on the login screen) |
| `VITE_PILOT_AREA_NAME` | e.g. `Jayanagar–BTM Layout` |
| `VITE_MAP_CENTER` | `lat,lon` of your route, e.g. `12.9250,77.5938` |

4. **Deploy**, then **Settings → Git → Production Branch**: your working branch until you merge to
   `main`.

## 7. Connect them

1. GitHub `production` environment → add the variable `ALLOWED_ORIGINS` =
   `https://<your-app>.vercel.app` (no trailing slash) → run **Deploy backend** again.
2. Supabase → **Authentication → URL Configuration** → Site URL `https://<your-app>.vercel.app`.

## 8. Check it works

- [ ] `<API_URL>/health` says ok, and `<API_URL>/docs` shows the API
- [ ] The app opens on your phone over mobile data
- [ ] **Engineer sign in** works, and so does **Try the demo account**
- [ ] Dashboard, repair list, analytics and settings load
- [ ] GitHub → Actions → **Nightly → Run workflow** succeeds (ticks D3)
- [ ] Photo reports need trained models: until `HF_MODEL_REPO` is set, submitting a photo
      shows an error. Everything else works.

## After the models exist

Add the variables `HF_MODEL_REPO` (`<hf-user>/roadsense-models`) and `MODEL_VERSION` to the
`production` environment and run **Deploy backend** (it bakes the models into the image). Copy
`yolo-nano.onnx` into `frontend/public/models/` for Drive mode.

## Before a demo

Open the app 5–10 minutes early: scale-to-zero means the first request loads the models.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| *Set up database* says a secret is missing | Add it under Settings → Environments → **production** (not repository secrets) |
| Migrations: `password authentication failed` | Wrong password in `DATABASE_URL`, or the `[ ]` brackets are still there |
| Migrations: timeout / can't resolve host | Use the **Session pooler** address (port 5432), not Direct |
| `type "geography" does not exist` | Switch on PostGIS (step 1.2) |
| Azure login fails in *Deploy backend* (`AADSTS70021`, no matching federated identity) | Run the Cloud Shell script again; the GitHub environment must be named exactly `production` |
| Smoke test fails, logs say `unauthorized` pulling the image | Make the `roadsense-api` package public (step 5.2) |
| Browser console: CORS error | `ALLOWED_ORIGINS` must exactly match the Vercel address, then redeploy |
| Sign-in works but screens say "Please sign in again" | The user has no row in `profiles` (re-run *Set up database*) or the JWT secret is wrong |
| See the backend's logs | Cloud Shell: `az containerapp logs show -n roadsense-api -g roadsense --follow` |
