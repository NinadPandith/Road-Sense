# Appendix A: API endpoints {.unnumbered}

| Method and path | Who | Purpose |
|-----------------|-----|---------|
| POST /reports | Anyone (rate-limited) | Photo or Drive-mode frame; returns the AI result and tracking code |
| POST /reports/{code}/send-anyway | Anyone | Send a no-damage photo to an engineer for review |
| GET /track/{code} | Anyone | Status timeline of a report |
| GET /defects | Engineer, demo | Ranked, filtered, paginated defects |
| GET /defects/{id} | Engineer, demo | Photos, severity and priority breakdown, history |
| PATCH /defects/{id}/status | Engineer | Change status (optionally with an after-repair photo) |
| POST /defects/bulk-status | Engineer | Change up to 100 defects at once |
| GET /repair-list.csv | Engineer, demo | Export the filtered repair list |
| POST /surveys, GET /surveys, GET /surveys/{id} | Engineer | Survey videos and job progress |
| GET /stats | Engineer, demo | Dashboard numbers and charts |
| GET /settings, POST /settings, GET /settings/history | Engineer | Weights, thresholds and their history |
| POST /admin/recalculate | Nightly job (secret header) | Recalculate all priorities |
| GET /health | Anyone | Status and model version |

Interactive documentation is generated automatically at `/docs` on the running API.

# Appendix B: Default settings (version 1) {.unnumbered}

```json
{
  "severity_weights": {"A": 0.35, "D": 0.35, "T": 0.20, "P": 0.10},
  "thresholds": {"moderate": 0.40, "dangerous": 0.70},
  "type_weights": {"pothole": 1.0, "alligator_crack": 0.7, "crack_across": 0.5, "crack_along": 0.4},
  "road_weights": {"major": 1.0, "secondary": 0.8, "tertiary": 0.6, "residential": 0.4, "unknown": 0.5},
  "merge_radius_m": 5, "min_confidence": 0.35, "sensitive_radius_m": 200,
  "sensitive_boost": 1.3, "auto_verify_reports": 3, "reopen_days": 30
}
```

# Appendix C: Source code {.unnumbered}

The full source code, documentation and notebooks are at
<https://github.com/NinadPandith/Road-Sense> under the AGPL-3.0 licence.
