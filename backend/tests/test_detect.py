"""B3: YOLO output decoding (no model weights needed)."""

import numpy as np

from app.models.enums import DamageClass
from app.services.detect import letterbox, nms, postprocess


def _raw(rows: list[tuple[float, float, float, float, int, float]], nc: int = 4) -> np.ndarray:
    """Build a fake 1 x (4+nc) x N YOLO output from (cx, cy, w, h, class, score) rows."""
    out = np.zeros((1, 4 + nc, len(rows)), np.float32)
    for i, (cx, cy, w, h, c, s) in enumerate(rows):
        out[0, :4, i] = (cx, cy, w, h)
        out[0, 4 + c, i] = s
    return out


def test_letterbox_pads_wide_image():
    lb = letterbox(np.zeros((360, 640, 3), np.uint8), 640)
    assert lb.tensor.shape == (1, 3, 640, 640)
    assert lb.scale == 1.0
    assert lb.pad_x == 0 and lb.pad_y == 140


def test_postprocess_maps_boxes_back_to_image_fractions():
    img_w, img_h = 1280, 720
    lb = letterbox(np.zeros((img_h, img_w, 3), np.uint8), 640)  # scale 0.5, pad_y 140
    raw = _raw([(320, 320, 64, 32, 3, 0.9)])  # centre of the letterboxed image
    (det,) = postprocess(raw, lb, img_w, img_h, conf_threshold=0.35)
    assert det.damage_class == DamageClass.pothole
    assert det.confidence == 0.9
    x1, y1, x2, y2 = det.box
    assert abs((x1 + x2) / 2 - 0.5) < 1e-3
    assert abs((y1 + y2) / 2 - 0.5) < 1e-3
    assert abs((x2 - x1) - 128 / 1280) < 1e-3


def test_postprocess_drops_low_confidence_and_overlaps():
    lb = letterbox(np.zeros((640, 640, 3), np.uint8), 640)
    raw = _raw(
        [
            (100, 100, 50, 50, 3, 0.9),
            (102, 101, 50, 50, 3, 0.8),  # duplicate of the first: suppressed
            (102, 101, 50, 50, 0, 0.7),  # same place, other class: kept (class-aware NMS)
            (400, 400, 50, 50, 1, 0.2),  # below threshold
        ]
    )
    dets = postprocess(raw, lb, 640, 640, conf_threshold=0.35)
    assert [(d.damage_class, d.confidence) for d in dets] == [
        (DamageClass.pothole, 0.9),
        (DamageClass.crack_along, 0.7),
    ]


def test_nms_keeps_separate_boxes():
    boxes = np.array([[0, 0, 10, 10], [20, 20, 30, 30]], np.float32)
    assert sorted(nms(boxes, np.array([0.5, 0.6]), 0.5)) == [0, 1]


def test_detector_runs_an_onnx_model(tmp_path):
    from app.services.detect import Detector
    from tests.onnx_fakes import constant_model

    raw = _raw([(320, 320, 64, 64, 3, 0.88), (100, 500, 40, 20, 1, 0.6)])
    path = tmp_path / "fake.onnx"
    constant_model(path, [1, 3, 640, 640], raw)
    dets = Detector(path).detect(np.zeros((640, 640, 3), np.uint8))
    assert [d.damage_class for d in dets] == [DamageClass.pothole, DamageClass.crack_across]
