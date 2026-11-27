# Testing

Testing was automated from the first module, so that later changes could not quietly break
earlier work. Every push runs all automated tests in GitHub Actions.

| Level | What is tested | Tool | Count |
|-------|----------------|------|-------|
| Unit | Severity and priority formulas, factor maths, class mapping, YOLO decoding, privacy blur, image checks, tracking codes, settings parsing | pytest | part of 93 |
| Spatial | Merge at 3 m but not at 6 m, location averaging, keep highest severity, auto-verify at 3 reports, re-open within 30 days but not after 40, ward and school lookups | pytest on real PostGIS | part of 93 |
| API | Every endpoint: success, validation errors, authentication, demo role blocked, allowed and refused status changes, rate limits, idempotent retries, CSV export | pytest + HTTP client on PostGIS | part of 93 |
| Survey worker | Video + GPX to defects with correct locations, de-duplication of consecutive frames, GPS mismatch failure, upload deletion | pytest with generated MP4 and GPX | part of 93 |
| Experiments | Severity evaluation, merge evaluation, segment split, dataset publishing (blur and EXIF removal) | pytest | 12 |
| Frontend unit | Copy rules (no exclamation marks, emoji, banned words), date and number formats, YOLO decoding in TypeScript, Drive-mode de-duplication, distance, offline outbox | Vitest | 26 |
| End to end | Citizen report flow, offline outbox, error messages, engineer flow, demo role, all admin screens | Playwright | 7 |
| Accessibility | WCAG 2 A/AA on every screen; fails on serious or critical issues | axe-core in Playwright | every screen |
| Manual | Phone in sunlight, slow 3G, offline, camera and location denied | Android phone | checklist |

Database tests run against a real Postgres with PostGIS, not a substitute database, because the
merge logic depends on PostGIS functions. Each test runs inside a transaction that is rolled back,
so tests never affect each other.

The full stack was also exercised in a browser during development with a stand-in model: a photo
report through to the result card and tracking page, merging of a second report 3 m away, Drive
mode with a simulated camera, a survey video processed into defects, and every engineer screen.

**Defects found by testing** included: a crash when the allowed origins were given as a
comma-separated list; an incompatible computer vision library version that had removed the face
detector; map plugins whose new major versions no longer worked with the map library; photos
stored in the browser database that did not survive on some browsers (fixed by storing bytes);
and two accessibility issues (an invalid list structure and charts that were hidden from screen
readers but still focusable).

[[Add the manual test checklist results from your phone here.]]
