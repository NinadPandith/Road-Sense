"""Fake services for API tests: no model weights, no network."""

import io
from pathlib import Path

import numpy as np
from PIL import Image

from app.models.enums import DamageClass, RoadClass
from app.services.detect import Detection
from app.services.geo import RoadInfo
from app.services.pipeline import Services
from app.services.storage import LocalStorage

LAT, LON = 12.9716, 77.5946  # a point in Bengaluru used across tests


def metres_north(lat: float, metres: float) -> float:
    return lat + metres / 111_320


class FakeDetector:
    def __init__(self) -> None:
        self.next: list[Detection] = [Detection(DamageClass.pothole, 0.9, (0.3, 0.55, 0.7, 0.95))]

    def detect(self, rgb, conf_threshold=0.35):
        return [d for d in self.next if d.confidence >= conf_threshold]


def fake_services(tmp: Path, detector: FakeDetector | None = None) -> Services:
    det = detector or FakeDetector()
    return Services(
        get_detector=lambda: det,
        get_depth=lambda: None,
        storage=LocalStorage(tmp, "http://test/local-storage"),
        road_lookup=lambda lat, lon: RoadInfo(RoadClass.major, "MG Road", 42),
        model_version="test-model",
    )


def road_photo(seed: int = 0) -> bytes:
    rng = np.random.default_rng(seed)
    arr = rng.integers(60, 200, (720, 1280, 3), dtype=np.uint8)
    out = io.BytesIO()
    Image.fromarray(arr).save(out, format="JPEG", quality=90)
    return out.getvalue()
