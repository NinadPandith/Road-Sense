# City data

| File | What | How to make it |
|------|------|----------------|
| `pilot_area.geojson` | The 10–15 km pilot route area (one polygon) | Draw it on geojson.io and save here |
| `wards.geojson` | Ward boundaries touching the pilot area; properties `code`, `name` | City corporation open data or OSM admin boundaries |
| `sensitive_places.geojson` | Optional offline copy of schools/hospitals; properties `kind`, `name`, `osm_id` | Or run `seed --fetch-osm` |

Set `PILOT_AREA_PATH` in the backend environment to enable the "outside the pilot area" check.
Until then, reports from anywhere are accepted.
