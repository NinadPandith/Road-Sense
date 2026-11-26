"""Relative depth with Depth Anything V2 Small (ONNX) for the severity D factor.

The model outputs relative inverse depth (bigger = closer). A pothole's floor is further from
the camera than the road around it, so its inverse depth is lower than its surroundings.
"""

import logging
from functools import lru_cache

import cv2
import numpy as np

from app.core.config import get_settings
from app.services.detect import model_path

log = logging.getLogger(__name__)

INPUT_SIZE = 518
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)

# How big a depth drop counts as "fully deep", as a share of the image's depth range.
# A calibration constant: tune it in experiments E3/E4 against hand labels.
FULL_DEPTH_SHARE = 0.08
RING_PAD = 0.5  # the comparison ring extends half a box width/height around the box


class DepthEstimator:
    def __init__(self, path: str) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, rgb: np.ndarray) -> np.ndarray:
        """Return an inverse-depth map with the same height and width as the image."""
        h, w = rgb.shape[:2]
        x = cv2.resize(rgb, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_CUBIC)
        x = ((x.astype(np.float32) / 255.0 - MEAN) / STD).transpose(2, 0, 1)[None]
        out = self.session.run(None, {self.input_name: x})[0]
        out = np.squeeze(out).astype(np.float32)
        return cv2.resize(out, (w, h), interpolation=cv2.INTER_LINEAR)


def depth_score(inv_depth: np.ndarray, box: tuple[float, float, float, float]) -> float | None:
    """D in 0-1: how much further the inside of the box is than the road ring around it."""
    h, w = inv_depth.shape
    x1, y1, x2, y2 = box
    bx1, by1, bx2, by2 = int(x1 * w), int(y1 * h), int(np.ceil(x2 * w)), int(np.ceil(y2 * h))
    if bx2 - bx1 < 2 or by2 - by1 < 2:
        return None
    pw, ph = int((bx2 - bx1) * RING_PAD), int((by2 - by1) * RING_PAD)
    rx1, ry1 = max(0, bx1 - pw), max(0, by1 - ph)
    rx2, ry2 = min(w, bx2 + pw), min(h, by2 + ph)

    ring_mask = np.zeros_like(inv_depth, dtype=bool)
    ring_mask[ry1:ry2, rx1:rx2] = True
    ring_mask[by1:by2, bx1:bx2] = False
    if ring_mask.sum() < 4:
        return None

    inside = float(np.median(inv_depth[by1:by2, bx1:bx2]))
    ring = float(np.median(inv_depth[ring_mask]))
    lo, hi = np.percentile(inv_depth, [5, 95])
    span = float(hi - lo)
    if span <= 1e-6:
        return 0.0
    drop = (ring - inside) / span
    return float(np.clip(drop / FULL_DEPTH_SHARE, 0.0, 1.0))


@lru_cache
def get_depth_estimator() -> DepthEstimator | None:
    """None when the depth model isn't available: severity then falls back to size + type."""
    try:
        return DepthEstimator(str(model_path(get_settings().depth_file)))
    except Exception as exc:  # noqa: BLE001 - depth is optional by design (PRD risk table)
        log.warning("Depth model unavailable, severity will skip D: %s", exc)
        return None
