import io

import numpy as np
import pytest
from PIL import Image

from app.core.errors import ApiError
from app.models.enums import DamageClass
from app.services.classes import class_from_index, confidence_label
from app.services.images import encode_jpeg, load_image, measure_quality, sniff_image_type


def test_class_mapping_follows_rdd2022_order():
    assert [class_from_index(i) for i in range(4)] == [
        DamageClass.crack_along,
        DamageClass.crack_across,
        DamageClass.alligator_crack,
        DamageClass.pothole,
    ]
    with pytest.raises(ValueError):
        class_from_index(4)


@pytest.mark.parametrize(
    ("conf", "label"),
    [
        (0.95, "very_likely"),
        (0.80, "very_likely"),
        (0.79, "likely"),
        (0.5, "likely"),
        (0.49, "possible"),
        (0.35, "possible"),
    ],
)
def test_confidence_words(conf, label):
    assert confidence_label(conf) == label


def _jpeg(arr: np.ndarray, **kw) -> bytes:
    out = io.BytesIO()
    Image.fromarray(arr).save(out, format="JPEG", **kw)
    return out.getvalue()


def test_sniff_checks_file_header_not_name():
    assert sniff_image_type(_jpeg(np.zeros((8, 8, 3), np.uint8))) == "image/jpeg"
    assert sniff_image_type(b"GIF89a....") is None
    assert sniff_image_type(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == "image/webp"


def test_load_image_rejects_non_images():
    with pytest.raises(ApiError) as e:
        load_image(b"not an image at all")
    assert e.value.code == "invalid_image"


def test_quality_flags_dark_and_flat_photos():
    rng = np.random.default_rng(0)
    textured = rng.integers(60, 200, (480, 640, 3), dtype=np.uint8)
    assert measure_quality(textured).ok
    dark = (textured // 10).astype(np.uint8)
    assert not measure_quality(dark).ok
    flat = np.full((480, 640, 3), 128, np.uint8)
    assert not measure_quality(flat).ok


def test_encode_jpeg_resizes_and_strips_exif():
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"
    big = np.zeros((3000, 4000, 3), np.uint8)
    data = _jpeg(big, exif=exif.tobytes())
    rgb = load_image(data)
    out = Image.open(io.BytesIO(encode_jpeg(rgb)))
    assert max(out.size) == 1280
    assert not out.getexif()
