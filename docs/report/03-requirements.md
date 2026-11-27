# Requirements and analysis

## Users

| User | Needs | Uses |
|------|-------|------|
| Municipal engineer | See where damage is, how bad it is, and what to fix first | Dashboard |
| Citizen | Report a pothole in under 30 seconds and see that it was acted on | Citizen view on a phone |
| Survey rider | Record a route once and have every defect logged | Drive mode, survey upload |
| Examiner / recruiter | Understand the novelty and see it working | Live demo, results page |

## Functional requirements

Priorities: **P0** must work for the minimum viable product, **P1** completes the project, **P2**
only if time allows.

| ID | Requirement | Priority | Status |
|----|-------------|----------|--------|
| D1 | Detect 4 classes in an image with box and confidence | P0 | Done |
| D2 | Process an uploaded video, sampling frames | P0 | Done (4 frames/s) |
| D3 | Reject photos without road damage | P0 | Done |
| D4 | Live detection in the phone browser (Drive mode) | P1 | Done |
| S1 | Severity score 0–1 and label for every detection | P0 | Done |
| S2 | Relative depth from a monocular depth model | P1 | Done |
| S3 | Show the severity breakdown in the interface | P1 | Done |
| G1 | GPS for photo reports (browser or EXIF) | P0 | Done |
| G2 | Match video frames to a GPS track by time | P1 | Done |
| G3 | Merge reports within 5 m into one defect | P0 | Done |
| G4 | Road type from OpenStreetMap | P1 | Done |
| R1 | Priority score and ranked repair list | P0 | Done |
| R2 | Boost near schools and hospitals | P1 | Done |
| R3 | Repair cost estimate | P2 | Not done |
| M1–M6 | Map with heatmap, filtered repair table, defect detail, status changes, CSV/PDF export, charts, results page | P0/P1 | Done |
| C1–C3 | Photo report, tracking code, installable PWA | P0/P1 | Done |
| C4 | Hindi interface | P2 | Prepared (all text in one file) |
| A1–A2 | Engineer login, rate limiting | P0/P1 | Done |

## Non-functional requirements

| Area | Requirement | How it is met |
|------|-------------|---------------|
| Performance | Photo result < 5 s; map loads < 2 s with 1,000 defects | Measured in E6; clustered map |
| Model size | Deployed detector ≤ 25 MB | YOLO11s/n ONNX ([[RESULT]] MB / [[RESULT]] MB) |
| Privacy | Blur faces and number plates before saving; no names or phone numbers | In-memory blur; EXIF stripped; anonymous citizens; IP stored only as a salted hash for 30 days |
| Security | Admin routes behind login; uploads ≤ 50 MB; per-IP rate limit | Supabase JWT, read-only demo role, file-header checks, 10 photos/hour |
| Cost | ₹0 running cost | Free tiers of Vercel, Supabase, Azure for Students, Hugging Face, Kaggle |
| Reliability | Model and API versioned | Every detection stores the model version |
| Usability | Report in 3 taps; works on an old Android phone | 44 px targets, 16 px text, resized uploads, offline outbox |
| Accessibility | WCAG AA | Automated axe checks on every screen in CI |
| Reproducibility | One-command setup; notebooks rerun end to end | Docker Compose; Kaggle notebooks |

## Feasibility

All components use free tiers or open-source software. Training needs a GPU only briefly, which
Kaggle provides (about 30 GPU hours a week). The laptop used for development has no NVIDIA GPU,
so all inference in the product runs on CPUs or in the phone browser.
