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
