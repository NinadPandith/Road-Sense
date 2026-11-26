"""B3: road damage detection with a YOLO model exported to ONNX (Ultralytics format).

The ONNX model takes a 1x3xSxS float image (RGB, 0-1, letterboxed) and returns
1 x (4 + num_classes) x N rows of (cx, cy, w, h, class scores...) in input pixels.
"""

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from app.core.config import get_settings
from app.models.enums import DamageClass
from app.services.classes import class_from_index

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    damage_class: DamageClass
    confidence: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 as fractions of width/height

    @property
    def area(self) -> float:
        x1, y1, x2, y2 = self.box
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    @property
    def centre_x(self) -> float:
        return (self.box[0] + self.box[2]) / 2


@dataclass(frozen=True)
class Letterbox:
    tensor: np.ndarray
    scale: float
    pad_x: float
    pad_y: float


def letterbox(rgb: np.ndarray, size: int = 640) -> Letterbox:
    """Resize keeping aspect ratio and pad to a square, like Ultralytics does."""
    h, w = rgb.shape[:2]
    scale = min(size / h, size / w)
    nh, nw = round(h * scale), round(w * scale)
    resized = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((size, size, 3), 114, dtype=np.uint8)
    pad_y, pad_x = (size - nh) / 2, (size - nw) / 2
    top, left = int(round(pad_y - 0.1)), int(round(pad_x - 0.1))
    canvas[top : top + nh, left : left + nw] = resized
    tensor = canvas.transpose(2, 0, 1)[None].astype(np.float32) / 255.0
    return Letterbox(tensor=tensor, scale=scale, pad_x=left, pad_y=top)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    """Plain non-maximum suppression on x1, y1, x2, y2 boxes. Returns kept indices."""
    order = scores.argsort()[::-1]
    keep: list[int] = []
    areas = (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])
    while order.size:
        i = int(order[0])
        keep.append(i)
        xx1 = np.maximum(boxes[i, 0], boxes[order[1:], 0])
        yy1 = np.maximum(boxes[i, 1], boxes[order[1:], 1])
        xx2 = np.minimum(boxes[i, 2], boxes[order[1:], 2])
        yy2 = np.minimum(boxes[i, 3], boxes[order[1:], 3])
        inter = np.clip(xx2 - xx1, 0, None) * np.clip(yy2 - yy1, 0, None)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[1:][iou <= iou_threshold]
    return keep


def postprocess(
    output: np.ndarray,
    lb: Letterbox,
    image_w: int,
    image_h: int,
    conf_threshold: float,
    iou_threshold: float = 0.5,
) -> list[Detection]:
    """Turn raw YOLO output into detections in image fractions (class-aware NMS)."""
    preds = output[0].T  # N x (4 + nc)
    scores_all = preds[:, 4:]
    cls = scores_all.argmax(axis=1)
    conf = scores_all[np.arange(len(preds)), cls]
    mask = conf >= conf_threshold
    if not mask.any():
        return []
    preds, cls, conf = preds[mask], cls[mask], conf[mask]
    cx, cy, bw, bh = preds[:, 0], preds[:, 1], preds[:, 2], preds[:, 3]
    boxes = np.stack([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], axis=1)
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - lb.pad_x) / lb.scale
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - lb.pad_y) / lb.scale
    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, image_w) / image_w
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, image_h) / image_h

    results: list[Detection] = []
    for c in np.unique(cls):
        idx = np.where(cls == c)[0]
        for k in nms(boxes[idx], conf[idx], iou_threshold):
            i = idx[k]
            results.append(
                Detection(
                    damage_class=class_from_index(int(c)),
                    confidence=round(float(conf[i]), 4),
                    box=tuple(round(float(v), 4) for v in boxes[i]),  # type: ignore[arg-type]
                )
            )
    results.sort(key=lambda d: d.confidence, reverse=True)
    return results


class Detector:
    def __init__(self, model_path: str | Path, input_size: int = 640) -> None:
        import onnxruntime as ort

        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name
        shape = self.session.get_inputs()[0].shape
        self.input_size = shape[2] if isinstance(shape[2], int) else input_size

    def detect(self, rgb: np.ndarray, conf_threshold: float = 0.35) -> list[Detection]:
        h, w = rgb.shape[:2]
        lb = letterbox(rgb, self.input_size)
        (output,) = self.session.run(None, {self.input_name: lb.tensor})[:1]
        return postprocess(output, lb, w, h, conf_threshold)


def model_path(filename: str) -> Path:
    """Local file if present (backend/models/), else download from the Hugging Face Hub."""
    settings = get_settings()
    local = Path(__file__).resolve().parents[2] / "models" / filename
    if local.exists():
        return local
    if not settings.hf_model_repo:
        raise FileNotFoundError(f"{filename} not found locally and HF_MODEL_REPO is not set")
    from huggingface_hub import hf_hub_download

    return Path(
        hf_hub_download(settings.hf_model_repo, filename, cache_dir=settings.model_cache_dir)
    )


@lru_cache
def get_detector() -> Detector:
    path = model_path(get_settings().detector_file)
    log.info("Loading detector from %s", path)
    return Detector(path)
