"""B11: export photos of defects engineers marked "Not a defect" (rejected) as hard negatives
for retraining. Run monthly (Backend Schema, retention).

Usage (from backend/):
    uv run python -m scripts.export_hard_negatives --out ../ml/data/hard_negatives \
        [--since 2026-12-01]

Writes the images plus labels.csv (file, report_id, defect_id, rejected_at, reason, ai_class,
ai_confidence). In YOLO training, add the images with empty label files as background images.
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.core.db import get_sessionmaker
from app.services.storage import REPORT_IMAGES, make_storage

QUERY = """
select r.id as report_id, r.image_path, d.id as defect_id, h.created_at as rejected_at, h.reason,
       (select det.damage_class::text from detections det where det.report_id = r.id
         order by det.confidence desc limit 1) as ai_class,
       (select max(det.confidence) from detections det where det.report_id = r.id) as ai_confidence
from defects d
join lateral (
  select created_at, reason from status_history
  where defect_id = d.id and to_status = 'rejected' order by created_at desc limit 1
) h on true
join reports r on r.defect_id = d.id
where d.status = 'rejected' and r.image_path is not null
  and (cast(:since as timestamptz) is null or h.created_at >= cast(:since as timestamptz))
order by h.created_at
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--since", type=datetime.fromisoformat)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    storage = make_storage()
    with get_sessionmaker()() as db:
        rows = db.execute(text(QUERY), {"since": a.since}).mappings().all()
    with (a.out / "labels.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            ["file", "report_id", "defect_id", "rejected_at", "reason", "ai_class", "ai_confidence"]
        )
        for r in rows:
            name = f"{r['report_id']}.jpg"
            (a.out / name).write_bytes(storage.download(REPORT_IMAGES, r["image_path"]))
            w.writerow(
                [
                    name,
                    r["report_id"],
                    r["defect_id"],
                    r["rejected_at"].isoformat(),
                    r["reason"] or "",
                    r["ai_class"] or "",
                    r["ai_confidence"] or "",
                ]
            )
    print(f"exported {len(rows)} hard negatives to {a.out}")


if __name__ == "__main__":
    main()
