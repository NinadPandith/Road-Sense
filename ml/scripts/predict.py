"""M4 check: run the exported ONNX detector on one image and print the boxes.

Uses the backend's detector code, so what you see here is exactly what the API does.

Usage (from the repo root):
    python ml/scripts/predict.py image.jpg --model backend/models/yolo-small.onnx [--save out.jpg]
"""

import argparse
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.detect import Detector  # noqa: E402

COLOURS = {
    "pothole": (0, 0, 220),
    "alligator_crack": (0, 140, 255),
    "crack_across": (0, 200, 200),
    "crack_along": (0, 180, 0),
}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image", type=Path)
    ap.add_argument("--model", type=Path, default=ROOT / "backend" / "models" / "yolo-small.onnx")
    ap.add_argument("--conf", type=float, default=0.35)
    ap.add_argument("--save", type=Path)
    a = ap.parse_args()

    bgr = cv2.imread(str(a.image))
    if bgr is None:
        sys.exit(f"cannot read {a.image}")
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    dets = Detector(a.model).detect(rgb, a.conf)
    h, w = bgr.shape[:2]
    if not dets:
        print("no road damage found")
    for d in dets:
        x1, y1, x2, y2 = d.box
        print(
            f"{d.damage_class.value:16s} {d.confidence:.2f}  "
            f"box=({x1 * w:.0f}, {y1 * h:.0f}, {x2 * w:.0f}, {y2 * h:.0f})"
        )
        if a.save:
            c = COLOURS[d.damage_class.value]
            cv2.rectangle(bgr, (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h)), c, 2)
            cv2.putText(
                bgr,
                f"{d.damage_class.value} {d.confidence:.2f}",
                (int(x1 * w), max(12, int(y1 * h) - 4)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                c,
                1,
            )
    if a.save:
        cv2.imwrite(str(a.save), bgr)
        print(f"saved {a.save}")


if __name__ == "__main__":
    main()
