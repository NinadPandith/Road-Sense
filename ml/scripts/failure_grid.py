"""M14: failure analysis - an annotated grid of 10-15 hard examples (speed breakers, shadows,
water-filled potholes...) with the model's boxes and a one-line note each.

Input CSV: file,note[,kind]  (kind: e.g. false_positive / missed / correct)
Usage (from the repo root):
    python ml/scripts/failure_grid.py ml/data/failures.csv --images ml/data/failures \
        --model backend/models/yolo-small.onnx --out ml/results/failure_grid.png
"""

import argparse
import csv
import sys
import textwrap
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.detect import Detector  # noqa: E402

COLOURS = {
    "pothole": (40, 40, 220),
    "alligator_crack": (0, 140, 255),
    "crack_across": (0, 170, 60),
    "crack_along": (0, 170, 60),
}
TILE_W, TILE_H, CAPTION_H = 420, 300, 70


def tile(bgr: np.ndarray, dets, note: str, kind: str) -> np.ndarray:
    h, w = bgr.shape[:2]
    for d in dets:
        x1, y1, x2, y2 = (
            int(d.box[0] * w),
            int(d.box[1] * h),
            int(d.box[2] * w),
            int(d.box[3] * h),
        )
        c = COLOURS[d.damage_class.value]
        cv2.rectangle(bgr, (x1, y1), (x2, y2), c, max(2, w // 300))
        cv2.putText(
            bgr,
            f"{d.damage_class.value} {d.confidence:.2f}",
            (x1, max(18, y1 - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            max(0.5, w / 1400),
            c,
            2,
        )
    img = cv2.resize(bgr, (TILE_W, TILE_H), interpolation=cv2.INTER_AREA)
    caption = np.full((CAPTION_H, TILE_W, 3), 255, np.uint8)
    lines = textwrap.wrap(f"[{kind}] {note}" if kind else note, 52)[:3]
    for i, line in enumerate(lines):
        cv2.putText(caption, line, (8, 20 + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 41, 59), 1)
    return np.vstack([img, caption])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", type=Path)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "ml" / "results" / "failure_grid.png")
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--conf", type=float, default=0.35)
    a = ap.parse_args()

    det = Detector(a.model)
    tiles = []
    for row in csv.DictReader(a.csv.open()):
        bgr = cv2.imread(str(a.images / row["file"]))
        if bgr is None:
            print(f"skipped unreadable {row['file']}")
            continue
        dets = det.detect(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB), a.conf)
        tiles.append(tile(bgr, dets, row["note"], row.get("kind", "")))
    if not tiles:
        sys.exit("no images")
    blank = np.full_like(tiles[0], 255)
    while len(tiles) % a.cols:
        tiles.append(blank)
    rows = [np.hstack(tiles[i : i + a.cols]) for i in range(0, len(tiles), a.cols)]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(a.out), np.vstack(rows))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
