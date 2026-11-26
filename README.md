# RoadSense

**RoadSense doesn't just detect potholes; it tells a city which one to fix first, and why.**

RoadSense finds road damage in phone photos and dashcam video, estimates how dangerous each defect is
(size, relative depth, damage type and position on the road), merges duplicate reports of the same
spot, and ranks repairs for municipal engineers on a live map.

> Status: in development (final-year B.Tech project). Live demo link, demo GIF and results table will
> be added here when the MVP is deployed.

## How it works

1. A citizen photographs a pothole (or a rider uses Drive mode, or an engineer uploads a survey video).
2. The backend blurs faces and number plates, then runs a YOLO detector (ONNX).
3. Each detection gets a severity score `S = 0.35·A + 0.35·D + 0.20·T + 0.10·P`
   (size, depth, type, position) and a label: Minor, Moderate or Dangerous.
4. Reports within 5 m of an open defect are merged into it (PostGIS).
5. Each defect gets a repair priority
   `S × R × (1 + 0.1·min(n, 10)) × (1 + 0.02·min(t, 30)) × B`
   (severity, road importance, number of reports, age, near a school/hospital), shown with its reasons.

## Repository layout

| Folder | What |
|--------|------|
| `frontend/` | React + Vite + TypeScript PWA: citizen view, Drive mode, engineer dashboard |
| `backend/` | FastAPI service: detection, severity, merging, priority, API |
| `ml/` | Training notebooks, dataset and export scripts, experiment results |
| `docs/` | PRD, app flow, tech stack, backend schema, content guidelines, implementation plan |

## Local setup

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js LTS with pnpm, and a
Supabase project (or a local Postgres with PostGIS).

```bash
cp .env.example .env   # fill in your values
```

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run python -m scripts.seed
```

```bash
cd backend && uv run uvicorn app.main:app --reload
```

```bash
cd frontend && pnpm install && pnpm dev
```

API docs are served at `http://localhost:8000/docs`.

## Licence

AGPL-3.0, because RoadSense uses Ultralytics YOLO (AGPL-3.0). See [LICENSE](LICENSE).
