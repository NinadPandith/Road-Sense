# RoadSense

**RoadSense doesn't just detect potholes; it tells a city which one to fix first, and why.**

RoadSense finds road damage in phone photos and dashcam video, estimates how dangerous each defect
is, merges duplicate reports of the same spot, and gives municipal engineers a ranked, explained
repair list on a live map.

[**Live demo**](https://YOUR-APP.vercel.app) · [Demo video (3 min)](https://youtu.be/YOUR-VIDEO) ·
[Results](https://YOUR-APP.vercel.app/results) · [Models on Hugging Face](https://huggingface.co/YOUR-HF-USER/roadsense-models) ·
[Local dataset](https://huggingface.co/datasets/YOUR-HF-USER/roadsense-local)

> Try the engineer dashboard with the read-only demo account: the login screen shows the
> credentials (**Try the demo account**).

![RoadSense demo](docs/images/demo.gif)
<!-- Record with the app open on a phone: report a pothole -> result card -> dashboard. Save as docs/images/demo.gif (≤ 8 MB). -->

## Why

Cities fix potholes by complaint, not by danger, so the most dangerous damage often waits longest.
In India potholes were linked to 2,161 deaths in 2023 (MoRTH, *Road Accidents in India 2023*),
and two-wheeler riders are hit hardest. Most research stops at detecting damage; RoadSense
measures **how severe** each defect is and turns that into a **repair priority** an engineer can
act on and explain.

## What it does

| For | What |
|-----|------|
| Citizens | Report a pothole in 3 taps with no account; GPS is added automatically; see the AI's result and track the report with a code like `RS-7K2Q` |
| Riders | **Drive mode**: the phone on the dashboard detects damage live in the browser and uploads only the frames with damage |
| Engineers | A ranked repair list with reasons ("Dangerous · main road · near school · 6 reports · 12 days open"), map with heatmap, status changes, CSV/PDF work orders, survey video upload, analytics |
| Examiners | A results page with model comparison, severity validation, ablation, merge accuracy, timing and failure cases |

## How it works

![Architecture](docs/images/prd/media/image1.png)

1. **Privacy first.** Faces and number plates are blurred in memory; an unblurred photo is never stored.
2. **Detect.** A YOLO11 model (ONNX) finds 4 damage types: pothole, alligator crack, crack across and along the road.
3. **Severity** per detection, from 0 to 1:
   `S = 0.35·A + 0.35·D + 0.20·T + 0.10·P` (size, relative depth from Depth Anything V2, damage
   type, position in the wheel path), labelled Minor / Moderate / Dangerous.
4. **Merge.** A report within 5 m of an open defect joins it (PostGIS); 3 reports auto-verify it.
5. **Priority.**
   `S × R × (1 + 0.1·min(n, 10)) × (1 + 0.02·min(t, 30)) × B`
   (severity, road importance from OpenStreetMap, number of reports, days open, school or hospital
   within 200 m). Every term is shown, so the ranking is explainable.

## Results

Measured on images the models never saw during training. Full tables and failure cases:
[results page](https://YOUR-APP.vercel.app/results) · source files in [`ml/results/`](ml/results).

| Experiment | Result |
|------------|--------|
| E1 Pothole detection (YOLO11s, RDD2022 India test) | mAP@0.5 **[[RESULT: E1 pothole AP@0.5]]** on [[RESULT: test images]] images |
| E2 Gain from local data (local test set) | **[[RESULT: E2 mAP gain]]** mAP@0.5 points |
| E3 Severity vs hand labels (held-out half) | accuracy [[RESULT: E3 accuracy]], weighted kappa [[RESULT: E3 kappa]] |
| E5 Duplicate merge accuracy (route ridden twice) | [[RESULT: E5 merge accuracy at 5 m]] |
| E6 Photo report, upload to result | [[RESULT: E6 median seconds]] s (median) |

## Tech stack

React + TypeScript + Vite PWA (Tailwind, TanStack Query, Leaflet, Recharts, ONNX Runtime Web) ·
FastAPI (Pydantic, SQLAlchemy, Alembic, ONNX Runtime, OpenCV) · Supabase (Postgres + PostGIS,
Storage, Auth, Realtime) · Ultralytics YOLO11 trained on Kaggle · Depth Anything V2 Small ·
Vercel + Azure Container Apps · GitHub Actions. Everything runs on free tiers.
Details and reasons: [docs/tech-stack.md](docs/tech-stack.md).

## Run it locally

You need [Docker](https://docs.docker.com/get-docker/) (with Compose).

```bash
git clone https://github.com/NinadPandith/Road-Sense.git
```

```bash
cd Road-Sense && HF_MODEL_REPO=YOUR-HF-USER/roadsense-models docker compose up --build
```

Open <http://localhost:5173> for the app and <http://localhost:8000/docs> for the API. Without
`HF_MODEL_REPO` the app runs, but reports can't be scored; you can also copy `yolo-small.onnx`
and `depth-anything-v2-small.onnx` into `backend/models/`. Engineer sign-in needs a free
Supabase project (see [docs/deployment.md](docs/deployment.md)); the citizen flow works without it.

<details>
<summary>Without Docker</summary>

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node.js 20+ with pnpm, and
Postgres 16 with PostGIS.

```bash
cp .env.example .env
```

```bash
psql postgresql://postgres:postgres@localhost:5432/roadsense -f backend/scripts/supabase_shim.sql
```

Run the line above only for a local Postgres (Supabase already has these parts), then:

```bash
cd backend && uv sync && uv run alembic upgrade head && uv run python -m scripts.seed
```

```bash
cd backend && uv run uvicorn app.main:app --reload
```

```bash
cd frontend && pnpm install && pnpm dev
```
</details>

### Tests

```bash
cd backend && TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/roadsense_test uv run pytest
```

```bash
cd frontend && pnpm test && pnpm e2e
```

```bash
cd ml && uv run pytest
```

CI runs all three, plus lint and accessibility checks (axe), on every push.

## Repository layout

| Folder | What |
|--------|------|
| [`frontend/`](frontend) | React PWA: citizen screens, Drive mode, engineer dashboard |
| [`backend/`](backend) | FastAPI: detection, severity, merging, priority, surveys, API |
| [`ml/`](ml) | Kaggle notebooks, dataset and export scripts, experiments E1–E6 |
| [`docs/`](docs) | PRD, app flow, tech stack, backend schema, content guidelines, plan, deployment, report |
| [`paper/`](paper) | IEEE conference paper draft |

## Limitations

- Depth is **relative**, never centimetres, and monocular depth models can smooth over shallow
  potholes; the ablation (E4) shows how much depth actually adds.
- The detector was trained on RDD2022 and one city's roads; accuracy elsewhere will differ.
- Speed breakers, wet patches and deep shadows cause false detections (see failure cases).
- Phone GPS is accurate to 5–15 m, which limits how finely reports can be merged.

## Licence and credits

AGPL-3.0, because RoadSense uses [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
(AGPL-3.0). See [LICENSE](LICENSE).

Built on the [RDD2022](https://arxiv.org/abs/2209.08538) dataset (Arya et al.),
[Depth Anything V2](https://arxiv.org/abs/2406.09414) (Small, Apache-2.0) and
[OpenStreetMap](https://www.openstreetmap.org/copyright) data. A final-year B.Tech project by
Ninad Pandith M N.
