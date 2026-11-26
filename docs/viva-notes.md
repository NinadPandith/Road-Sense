# Viva notes

Five questions an examiner may ask after each module, with answers in my own words.
Add a section per task ID as it is finished.

## B1: database schema and migrations

1. **Why Postgres + PostGIS and not Firebase?** The core of the project is spatial: "is there an open
   defect within 5 m?" PostGIS answers that with `ST_DWithin` on a GiST index in milliseconds.
2. **Why `geography(Point, 4326)` instead of `geometry`?** Geography measures distances in metres on
   the earth's surface, so `ST_DWithin(location, point, 5)` really means 5 metres.
3. **Why are reports and defects separate tables?** A report is one photo; a defect is one damaged
   spot. Many reports merge into one defect, which is how duplicates are removed.
4. **What does Row Level Security do here?** Citizens (anon role) can only read the
   `public_defects` view and lookup tables; signed-in staff can read everything; all writes go
   through FastAPI with the service role.
5. **Why Alembic?** Every schema change is a versioned file, so any database (local, CI, Supabase)
   can be rebuilt to the same state with `alembic upgrade head`.

## B2: FastAPI skeleton

1. **Why FastAPI?** Same language as the ML code, typed request/response models with Pydantic, and
   automatic OpenAPI docs at `/docs`.
2. **How is configuration handled?** `pydantic-settings` reads environment variables (12-factor),
   so secrets never live in the code.
3. **Why one error shape?** The frontend can map `error.code` to a friendly message from the
   Content Guidelines without parsing text.
4. **How is a DB session managed per request?** A FastAPI dependency opens a session, commits on
   success and rolls back on any exception.
5. **How do tests avoid polluting the database?** Each test runs inside a transaction that is
   rolled back at the end.

## D1: CI

1. **What runs on every push?** Ruff lint/format, pytest against a real PostGIS service container,
   and (once it exists) frontend lint, tests and build.
2. **Why a real PostGIS in CI instead of SQLite?** The merge logic depends on PostGIS functions;
   SQLite would test something different from production.
3. **What is `uv sync --frozen`?** Installs exactly the versions in `uv.lock`, so CI matches my
   laptop.
4. **Why mark tests as `slow`?** Tests on real model weights are skipped in CI to keep it fast.
5. **How does CI help with AI-written code?** Generated code that breaks an earlier module fails
   the tests before it is merged.

## B3: detection (YOLO + ONNX)

1. **What does the ONNX model output?** A tensor of 8,400 candidate boxes, each with centre x/y,
   width, height and one score per class.
2. **What is letterboxing?** Resizing the photo to fit 640x640 without stretching, padding the rest
   with grey; the boxes are mapped back by removing the padding and dividing by the scale.
3. **What is non-maximum suppression?** When several boxes overlap the same pothole (IoU > 0.5),
   only the most confident one is kept. It runs per class.
4. **Why ONNX instead of PyTorch on the server?** One file runs everywhere (server CPU, laptop,
   phone browser) and ONNX Runtime is much lighter than PyTorch.
5. **Why a confidence threshold of 0.35?** It is the setting `min_confidence`; low enough to catch
   most potholes, and the citizen still sees "Possible" for weak detections.

## B4: privacy blur

1. **When is the image blurred?** In memory, before the first upload. The unblurred original is
   never written to storage.
2. **How are faces and plates found?** v1 uses OpenCV's built-in Haar cascades (frontal face,
   profile face, number plate); a YOLO face/plate model can replace them later.
3. **Why pixelate and then blur?** Pixelation removes detail that a plain blur can sometimes leave
   recoverable; the blur on top makes it look clean.
4. **What else is removed?** All EXIF metadata; GPS and time are stored in the database row instead.
5. **What are the limits?** Haar cascades miss small or angled faces. This is listed as a known
   limitation and an ethics point in the report.

## M8: severity score

1. **What is the formula?** S = 0.35·A + 0.35·D + 0.20·T + 0.10·P, with labels Minor < 0.40,
   Moderate 0.40–0.69, Dangerous ≥ 0.70. Weights come from the active settings row.
2. **How is size (A) measured?** The part of the box inside the road region (lower 55% of the
   frame) divided by that region's area, saturating at 20% of the road.
3. **How is depth (D) measured?** Depth Anything V2 gives relative inverse depth. I compare the
   median inside the box with a ring of road around it; a pothole floor is further away. The drop is
   scaled by the image's depth range, so it is relative, never centimetres.
4. **What if the depth model fails?** D is skipped and the other weights are rescaled to sum to 1,
   so the score stays comparable (the PRD's fallback to size + type).
5. **How do you know the score is right?** Experiment E3: compare with 200 hand labels (accuracy,
   weighted kappa), tune weights on half the data, and E4 ablates each factor.

## B5: POST /reports pipeline

1. **What are the 9 steps?** Check (file type, size, rate limit, pilot area) → save report →
   blur → detect → score → merge → enrich → prioritise → respond.
2. **Why blur before saving, when the App Flow says save first?** The Backend Schema rule wins: an
   unblurred original must never reach storage, so blurring happens in memory first.
3. **What if the AI finds nothing?** The report is saved as `no_damage` and the citizen can choose
   *Send anyway*, which creates a `needs_review` defect for an engineer.
4. **How do offline retries avoid duplicates?** Each report carries a `client_report_id`
   (idempotency key); a second upload with the same ID returns the first result.
5. **How is spam limited?** 10 reports per IP per hour, counted in the database with a salted
   SHA-256 hash of the IP (the raw IP is never stored, and hashes are cleared after 30 days).

## B6: merging duplicate reports

1. **How is "the same pothole" decided?** `ST_DWithin(location, point, 5 m)` on open defects (and
   ones fixed in the last 30 days), nearest first.
2. **Why PostGIS instead of DBSCAN at request time?** Reports arrive one at a time; a radius query
   on a GiST index is the online version of DBSCAN with eps = 5 m and min_samples = 1. DBSCAN is
   still used offline in experiment E5.
3. **What stops two simultaneous reports from creating two defects?** Transaction-level advisory
   locks on the grid cells the 5 m circle touches, plus `SELECT … FOR UPDATE` on the defect row.
4. **What happens to the location and severity on merge?** The defect moves to the average of its
   reports, and keeps the highest severity seen.
5. **What is auto-verify and re-open?** At 3 reports a `reported` defect becomes `verified`
   automatically; a new report on a defect fixed less than 30 days ago re-opens it.

## B7: enrichment

1. **Where does road type come from?** OpenStreetMap via the Overpass API: the nearest `highway`
   way within 20 m, mapped to major/secondary/tertiary/residential.
2. **What if Overpass is down?** Road class becomes `unknown` (R = 0.5) and the report still goes
   through; lookups are cached by rounded coordinates.
3. **How is "near a school or hospital" found?** A 200 m `ST_DWithin` query on the seeded
   `sensitive_places` table.
4. **How is the ward found?** `ST_Covers(ward boundary, point)`.
5. **Why enrich only new defects?** The location of a merged defect moves by a few metres at most,
   so the road, ward and nearby places don't change.

## B8: priority

1. **What is the formula?** S × R × (1 + 0.1·min(n, 10)) × (1 + 0.02·min(t, 30)) × B.
2. **Why the caps?** So 50 reports or a year-old defect can't outrank a dangerous new pothole on a
   main road: reports add at most ×2, age at most ×1.6.
3. **How is the ranking explained?** Every term is stored in `priority_terms` and shown on the
   detail screen, plus a reason line like "Dangerous · main road · near school · 6 reports".
4. **Why recalculate nightly?** The age term t grows every day even when nothing else changes.
5. **What happens when an engineer changes the weights?** A new `settings_versions` row is saved
   (audit trail) and all open priorities are recalculated.

## B9: staff API and auth

1. **How do engineers log in?** Supabase Auth issues a JWT; FastAPI verifies its signature
   (HS256 secret or the project's JWKS) and looks up the user's role in `profiles`.
2. **How is the demo account kept read-only?** Every write endpoint depends on
   `require_engineer`, which returns 403 `forbidden_demo` for the demo role.
3. **Which status changes are allowed?** needs_review → reported/rejected; reported →
   verified/assigned/rejected; verified → assigned/rejected; assigned → fixed/rejected. Anything
   else is 409 `invalid_transition`. Fixed → reported happens only when a new report re-opens it.
4. **How is the rank computed?** A window function, `rank() over (order by priority desc)`, over
   open defects only, so filters don't change a defect's global rank.
5. **How is the nightly endpoint protected?** A shared `CRON_SECRET` header known only to the
   backend and the GitHub Actions secret store.

## F1–F3: frontend

1. **Why one React app for citizens and engineers?** One codebase and one deploy; admin screens
   are lazy-loaded so the citizen flow stays small on phones.
2. **Why is every string in en.json?** The Content Guidelines require it, and Hindi later becomes
   a translation job. A test checks the copy rules (no "!", no emoji, no banned words).
3. **How does the phone save data?** Photos are resized to 1280 px in the browser before upload.
4. **How is severity shown accessibly?** Always a word + colour + icon; bars have
   `role="meter"` with a text value; alerts use `aria-live`.
5. **How do citizens track without an account?** The tracking code is saved in the phone's local
   storage; the status page polls the API every 30 s.

## D2–D3: deployment

1. **Where does each part run?** React on Vercel, FastAPI in a container on Azure Container Apps
   (scale to zero), Postgres/Storage/Auth on Supabase, models on the Hugging Face Hub.
2. **What happens on a push to main?** CI runs lint and tests; the deploy workflow builds the
   image, pushes it to GHCR, runs Alembic migrations and updates the container app.
3. **What is a cold start?** With zero replicas, the first request starts a container and loads
   the models (20–40 s). Models can be baked into the image to shorten it.
4. **Why a nightly job?** It recalculates priorities, clears old IP hashes and keeps the free
   Supabase project from pausing.
5. **How are secrets handled?** Only in environment variables and GitHub/Azure secret stores;
   `.env` is git-ignored and the browser only ever gets the anon key.

## B10: survey processing

1. **How does a survey become defects?** The video and GPX are uploaded, a worker thread claims
   the job (`FOR UPDATE SKIP LOCKED`), samples 4 frames per second, detects on each, finds each
   frame's position by interpolating the GPX track at the frame's time, and sends the kept frames
   through the same pipeline as citizen photos.
2. **How is the video matched to GPS?** The video's start time comes from the MP4 header (mvhd
   creation time, UTC); frame time = start + offset. Without it, the GPX start is used.
3. **Why not save every frame?** The same pothole appears in many frames. Consecutive detections
   within 2 s and 5 m count as one defect, and only that best frame is stored (storage rule:
   only frames with detections).
4. **Why a jobs table instead of Celery?** A few videos a week don't justify hosting Redis; a
   polled table is simple, survives restarts (stale jobs are re-queued) and is visible in SQL.
5. **What happens to the uploads?** They are deleted as soon as the job is done or failed
   (retention rule).

## B11: needs review and Not a defect

1. **What is Needs review?** A photo the AI found no damage in, which the citizen sent anyway.
2. **What does Accept do?** Moves it to Reported with the engineer's damage type and severity,
   so it gets a priority.
3. **What does Not a defect do?** Moves the defect to Rejected (kept, never deleted) and its
   photos become hard negatives for retraining (`export_hard_negatives.py`).
4. **Why keep rejected defects?** Audit trail, and false positives are the most useful data for
   the next model.
5. **Can the AI overrule an engineer?** No. Status changes are engineer decisions; the AI only
   suggests.

## F4: Drive mode

1. **Where does detection run?** In the phone's browser with ONNX Runtime Web: WebGPU when
   available, WASM otherwise. The YOLO nano model is about 6–12 MB and is cached.
2. **How are duplicate uploads avoided?** The same defect in consecutive frames within 2 s is
   kept once, as the highest-confidence frame.
3. **What if the phone is too slow?** Below 2 frames per second it offers to send a photo every
   2 seconds instead, so the server does the detection.
4. **What if there's no signal?** Frames wait in an IndexedDB outbox and upload later, each with
   a client_report_id so retries don't duplicate.
5. **Why a separate rate limit?** A ride can find dozens of potholes, so Drive mode allows 120
   uploads per hour per network, counted separately from citizen photos (10 per hour).

## F5–F7: surveys screen, dashboard extras, PWA

1. **How does upload progress work?** `XMLHttpRequest` upload events (fetch can't report upload
   progress).
2. **How does the dashboard update live?** Supabase Realtime on the defects table; on any change
   the lists and KPIs are refetched (debounced by 1 s).
3. **Why cluster markers?** Hundreds of overlapping markers are unreadable when zoomed out;
   clusters split as you zoom in. The heatmap weights points by severity.
4. **What makes it an installable app?** A web manifest and a service worker (vite-plugin-pwa).
   The service worker caches the app shell, the Drive-mode model and map tiles.
5. **How are charts made accessible?** Colours validated for colour blindness, every chart has a
   table view, and severity always has a word and an icon.

## M10–M14, F8: experiments and results

1. **How is overfitting the severity weights avoided?** Weights are tuned on one stratified half
   of the 200 hand labels and reported on the other half only.
2. **Why weighted kappa and not just accuracy?** Labels are ordered; calling a Dangerous pothole
   Minor is worse than calling it Moderate, and kappa also corrects for chance agreement.
3. **What does the ablation show?** How much agreement drops when each factor is removed, i.e.
   whether depth is worth the extra model.
4. **How is merge accuracy defined?** The share of real potholes whose reports all land in one
   map point that contains no other pothole, measured over a sweep of radii.
5. **How are results kept honest?** Only real measurements go in `ml/results`; the results page
   shows test-set sizes and failure cases, and says "Not measured yet" until an experiment runs.

## D4: monitoring and accessibility

1. **What does Sentry collect?** Errors from both apps, without personal data: request bodies,
   cookies, IPs and auth headers are stripped before sending.
2. **How is accessibility checked?** Playwright end-to-end tests run axe (WCAG 2 A/AA) on every
   screen and fail on serious or critical issues; they run in CI.
3. **What did the checks catch?** An invalid list structure in the severity bars, and charts
   hidden from screen readers while still keyboard-focusable. Both were fixed.
4. **Why mock the API in end-to-end tests?** The tests then run with only the frontend dev
   server, quickly and reliably in CI; the full stack was also checked by hand against PostGIS.
5. **What else supports outdoor use?** 16 px text, 44 px touch targets, strong contrast and
   word + icon for every severity.
