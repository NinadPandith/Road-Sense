"""M9/M11: export potholes for hand labelling, keeping the AI's scores in a separate file so
labels are made before looking at them (PRD, severity validation).

Writes two CSVs:
  labelling_sheet.csv  id,image_url,box   -> add a 'label' column: minor / moderate / dangerous
  factors.csv          id,size,depth,type,position,score,ai_label  -> don't open until labelled

Usage (from backend/):
    uv run python -m scripts.export_severity_factors --out ../ml/data/severity --limit 200
Then join them into ml/data/severity_eval.csv (id,label,size,depth,type,position) and run
    python -m scripts.eval_severity data/severity_eval.csv   (from ml/)
"""

import argparse
import csv
import random
from pathlib import Path

from sqlalchemy import text

from app.core.db import get_sessionmaker
from app.services.storage import REPORT_IMAGES, make_storage

QUERY = """
select d.id, r.image_path, d.box, d.size_score, d.depth_score, d.type_score,
       d.position_score, d.severity_score, d.severity_label::text as ai_label
from detections d join reports r on r.id = d.report_id
where d.damage_class = 'pothole' and r.image_path is not null
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args()
    storage = make_storage()
    with get_sessionmaker()() as db:
        rows = list(db.execute(text(QUERY)).mappings())
    random.Random(a.seed).shuffle(rows)
    rows = rows[: a.limit]
    a.out.mkdir(parents=True, exist_ok=True)
    with (a.out / "labelling_sheet.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "image_url", "box", "label"])
        for r in rows:
            box = " ".join(f"{v:.3f}" for v in r["box"])
            w.writerow([r["id"], storage.public_url(REPORT_IMAGES, r["image_path"]), box, ""])
    with (a.out / "factors.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "size", "depth", "type", "position", "score", "ai_label"])
        for r in rows:
            w.writerow(
                [
                    r["id"],
                    r["size_score"],
                    "" if r["depth_score"] is None else r["depth_score"],
                    r["type_score"],
                    r["position_score"],
                    r["severity_score"],
                    r["ai_label"],
                ]
            )
    print(f"wrote {len(rows)} rows to {a.out}")


if __name__ == "__main__":
    main()
