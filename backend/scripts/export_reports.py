"""M12: export the reports of one or more surveys (e.g. the same route ridden twice) for
experiment E5. Add a pothole_id column by looking at the photos, then run
ml/scripts/eval_merge.py on the file.

Usage (from backend/):
    uv run python -m scripts.export_reports --survey <id-ride-1> --survey <id-ride-2> \
        --out ../ml/data/merge_eval.csv
"""

import argparse
import csv
import uuid
from pathlib import Path

from sqlalchemy import text

from app.core.db import get_sessionmaker
from app.services.storage import REPORT_IMAGES, make_storage


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--survey", action="append", type=uuid.UUID, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    storage = make_storage()
    with get_sessionmaker()() as db:
        rows = (
            db.execute(
                text(
                    "select r.id, r.survey_id, ST_Y(r.location::geometry) lat, "
                    "ST_X(r.location::geometry) lon, r.image_path from reports r "
                    "where r.survey_id = any(:ids) order by r.survey_id, r.captured_at"
                ),
                {"ids": a.survey},
            )
            .mappings()
            .all()
        )
    ride = {sid: i + 1 for i, sid in enumerate(a.survey)}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["report_id", "ride", "lat", "lon", "image_url", "pothole_id"])
        for r in rows:
            url = storage.public_url(REPORT_IMAGES, r["image_path"]) if r["image_path"] else ""
            w.writerow([r["id"], ride[r["survey_id"]], r["lat"], r["lon"], url, ""])
    print(f"wrote {len(rows)} reports to {a.out}; fill in pothole_id by looking at the photos")


if __name__ == "__main__":
    main()
