"""B4: faces and plates are blurred in memory."""

import pathlib

import numpy as np
from PIL import Image

from app.services.privacy import anonymise, blur_regions

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "face.jpg"


def test_blur_regions_changes_only_the_region():
    rng = np.random.default_rng(1)
    img = rng.integers(0, 255, (200, 200, 3), dtype=np.uint8)
    out = blur_regions(img, [(50, 50, 40, 40)], pad=0)
    assert np.array_equal(out[:40], img[:40])  # untouched above the box
    region = out[50:90, 50:90].astype(float)
    assert region.std() < img[50:90, 50:90].astype(float).std() / 3


def test_photo_with_a_face_comes_out_blurred():
    img = np.asarray(Image.open(FIXTURE).convert("RGB"))
    out, n = anonymise(img)
    assert n >= 1
    assert not np.array_equal(out, img)
    assert out.shape == img.shape
