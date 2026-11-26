"""B4: blur faces and number plates in memory, before anything is stored.

v1 uses OpenCV's bundled Haar cascades (no extra download). A YOLO face/plate ONNX model can
replace `find_regions` later without changing callers.
"""

from functools import lru_cache

import cv2
import numpy as np

Box = tuple[int, int, int, int]  # x, y, w, h in pixels


@lru_cache
def _cascades() -> tuple[cv2.CascadeClassifier, ...]:
    names = (
        "haarcascade_frontalface_default.xml",
        "haarcascade_profileface.xml",
        "haarcascade_russian_plate_number.xml",
    )
    return tuple(cv2.CascadeClassifier(cv2.data.haarcascades + n) for n in names)


def find_regions(rgb: np.ndarray) -> list[Box]:
    grey = cv2.equalizeHist(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY))
    min_side = max(20, min(grey.shape) // 40)
    boxes: list[Box] = []
    for cascade in _cascades():
        found = cascade.detectMultiScale(
            grey, scaleFactor=1.1, minNeighbors=5, minSize=(min_side, min_side)
        )
        boxes.extend(tuple(int(v) for v in b) for b in found)  # type: ignore[misc]
    return boxes


def blur_regions(rgb: np.ndarray, boxes: list[Box], pad: float = 0.15) -> np.ndarray:
    """Return a copy with each region (plus padding) heavily blurred."""
    out = rgb.copy()
    h, w = out.shape[:2]
    for x, y, bw, bh in boxes:
        px, py = int(bw * pad), int(bh * pad)
        x1, y1 = max(0, x - px), max(0, y - py)
        x2, y2 = min(w, x + bw + px), min(h, y + bh + py)
        if x2 <= x1 or y2 <= y1:
            continue
        roi = out[y1:y2, x1:x2]
        k = max(15, (max(x2 - x1, y2 - y1) // 3) | 1)
        small = cv2.resize(
            roi, (max(1, (x2 - x1) // 12), max(1, (y2 - y1) // 12)), interpolation=cv2.INTER_AREA
        )
        pixelated = cv2.resize(small, (x2 - x1, y2 - y1), interpolation=cv2.INTER_NEAREST)
        out[y1:y2, x1:x2] = cv2.GaussianBlur(pixelated, (k, k), 0)
    return out


def anonymise(rgb: np.ndarray) -> tuple[np.ndarray, int]:
    """Blur every face and plate found. Returns the new image and how many regions were blurred."""
    boxes = find_regions(rgb)
    return blur_regions(rgb, boxes), len(boxes)
