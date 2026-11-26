"""Upload validation, quality checks and resizing for report images."""

import io
from dataclasses import dataclass

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core.errors import ApiError

MAX_SIDE = 1280
THUMB_SIDE = 320
JPEG_QUALITY = 80

# Simple quality gates; tuned on a handful of phone photos. Too strict = angry citizens.
MIN_MEAN_BRIGHTNESS = 35  # 0-255
MIN_SHARPNESS = 15.0  # variance of the Laplacian on a 640 px grey image

_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
)


def sniff_image_type(data: bytes) -> str | None:
    """Check the file header, not the client's content type."""
    for magic, mime in _MAGIC:
        if data.startswith(magic):
            return mime
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def load_image(data: bytes) -> np.ndarray:
    """Decode an upload into an RGB uint8 array, upright (EXIF orientation applied)."""
    if sniff_image_type(data) is None:
        raise ApiError("invalid_image", 415)
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ApiError("invalid_image", 415) from exc
    return np.asarray(img)


def resize_max(rgb: np.ndarray, max_side: int) -> np.ndarray:
    h, w = rgb.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1:
        return rgb
    return cv2.resize(rgb, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)


@dataclass(frozen=True)
class Quality:
    brightness: float
    sharpness: float

    @property
    def ok(self) -> bool:
        return self.brightness >= MIN_MEAN_BRIGHTNESS and self.sharpness >= MIN_SHARPNESS


def measure_quality(rgb: np.ndarray) -> Quality:
    grey = cv2.cvtColor(resize_max(rgb, 640), cv2.COLOR_RGB2GRAY)
    return Quality(
        brightness=float(grey.mean()),
        sharpness=float(cv2.Laplacian(grey, cv2.CV_64F).var()),
    )


def encode_jpeg(rgb: np.ndarray, max_side: int = MAX_SIDE) -> bytes:
    """JPEG with no EXIF at all (GPS and time live in the reports row)."""
    out = io.BytesIO()
    Image.fromarray(resize_max(rgb, max_side)).save(
        out, format="JPEG", quality=JPEG_QUALITY, optimize=True
    )
    return out.getvalue()
