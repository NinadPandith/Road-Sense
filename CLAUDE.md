# RoadSense — rules for AI coding tools

RoadSense detects road damage from phone photos and video, scores how dangerous each defect is,
merges duplicate reports, and gives a city a ranked repair list on a live map.

**Always read `docs/` before working. The docs are the source of truth.**

| Doc | Use it for |
|-----|------------|
| `docs/PRD.md` | Requirements (P0/P1/P2), severity + priority formulas, experiments |
| `docs/app-flow.md` | The 15 screens (P1–P8, A1–A7), user flows, 9-step backend sequence, error states |
| `docs/tech-stack.md` | Technologies, repo layout, env vars, hosting |
| `docs/backend-schema.md` | Tables, enums, queries, RLS, storage buckets, API shapes, error codes |
| `docs/content-guidelines.md` | Every word in the UI |
| `docs/implementation-plan.md` | Task IDs (M/B/F/D/W), order and "done when" |

Where docs disagree, the more specific, newer doc wins: Backend Schema > Tech Stack > App Flow > PRD.
Notable resolved conflicts:
- Images are blurred **in memory before the first upload**; an unblurred original is never stored.
- Storage buckets: `report-images` (public), `fixed-photos` (public), `survey-uploads` (private).
- Backend hosting: Azure Container Apps (fallback Modal), not Hugging Face Spaces.
- Severity code lives in `backend/app/services/severity.py`.
- Weights, thresholds and radii are read from the newest `settings_versions` row, never hard-coded
  outside `backend/app/services/settings.py` defaults.

## Stack

- Frontend: React + TypeScript + Vite, React Router, Tailwind CSS, TanStack Query, react-leaflet,
  Recharts, i18next, vite-plugin-pwa, onnxruntime-web. Package manager: pnpm.
- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 + GeoAlchemy2, Alembic, ONNX Runtime,
  OpenCV, slowapi. Package manager: uv. Lint/format: Ruff.
- Data: Supabase Postgres + PostGIS, Supabase Storage, Supabase Auth, Supabase Realtime.
- ML: Ultralytics YOLO (trained on Kaggle) exported to ONNX; Depth Anything V2 Small ONNX.

## Folder layout

```text
frontend/   React PWA (src/pages one folder per screen, src/components, src/lib, src/locales)
backend/    FastAPI (app/api, app/core, app/services, app/models, app/schemas, alembic, tests, scripts)
ml/         notebooks/, scripts/, results/, data/
docs/       all specs + viva-notes.md
.github/workflows/  ci.yml, deploy.yml, nightly.yml
```

## Coding rules

- One task ID per session/commit. Commit message: `<ID>: <what>` e.g. `B6: merge reports within 5 m`.
- Every service file has pytest tests. Spatial tests (merge at 5 m, not at 6 m) must pass.
- Backend: type hints everywhere; Pydantic models for every request/response; errors use the shared
  shape `{"error": {"code", "message", "retry_after_s?"}}` with codes from the Backend Schema.
- Model class index → damage_class mapping lives only in `backend/app/services/classes.py`.
- Never commit secrets. Config comes from env vars (see `.env.example`).
- After each module, add 5 viva questions + answers to `docs/viva-notes.md`.

## Content rules (from docs/content-guidelines.md)
- All UI text lives in frontend/src/locales/en.json (i18next). Never hard-code strings.
- Use copy from the "Screen-by-screen copy" table exactly when it exists.
- Sentence case everywhere. Buttons: verb first, 1-3 words.
- Indian/British spelling (colour, centre). Dates like 27 Nov 2026. Times like 6:30 pm.
- Citizen screens say "pothole" and "report"; admin screens say "defect".
- Damage types: Pothole, Alligator crack, Crack across road, Crack along road.
- Severity labels: Minor (green, circle), Moderate (amber, triangle), Dangerous (red, diamond).
- Errors: what happened + what to do + a button. No "Oops", no error codes.
- No exclamation marks except "Thanks!" on success. No emoji. No ALL CAPS.
- Never promise repairs or dates. Never claim the AI is always right.
- Every icon button has an aria-label; every image has alt text.

## Commands

```bash
# backend
cd backend && uv sync && uv run uvicorn app.main:app --reload
cd backend && uv run pytest && uv run ruff check . && uv run ruff format --check .
# frontend
cd frontend && pnpm install && pnpm dev
cd frontend && pnpm lint && pnpm test && pnpm build
```
