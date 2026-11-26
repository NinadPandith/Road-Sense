"""M8: severity formula, factor maths and labels."""

import numpy as np
import pytest

from app.models.enums import DamageClass, SeverityLabel
from app.services.depth import depth_score
from app.services.detect import Detection
from app.services.severity import (
    combine,
    label_for,
    position_score,
    reason,
    score_detection,
    size_score,
)


def test_formula_matches_prd_weights():
    # S = 0.35A + 0.35D + 0.20T + 0.10P
    assert combine(0.5, 0.5, 1.0, 1.0) == pytest.approx(0.35 * 0.5 + 0.35 * 0.5 + 0.2 + 0.1)
    assert combine(1, 1, 1, 1) == pytest.approx(1.0)
    assert combine(0, 0, 0, 0) == 0.0


def test_missing_depth_rescales_other_weights():
    # Without D, the weights 0.35/0.20/0.10 are rescaled to sum to 1.
    assert combine(1, None, 1, 1) == pytest.approx(1.0)
    assert combine(0.5, None, 1.0, 1.0) == pytest.approx((0.175 + 0.2 + 0.1) / 0.65)


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (0.0, "minor"),
        (0.39, "minor"),
        (0.40, "moderate"),
        (0.69, "moderate"),
        (0.70, "dangerous"),
        (1.0, "dangerous"),
    ],
)
def test_labels_use_prd_thresholds(score, label):
    assert label_for(score) == SeverityLabel(label)


def test_position_is_one_at_centre_and_point_three_at_edge():
    assert position_score(0.5) == 1.0
    assert position_score(0.55) == 1.0
    assert position_score(0.0) == pytest.approx(0.3)
    assert position_score(1.0) == pytest.approx(0.3)
    assert 0.3 < position_score(0.25) < 1.0


def test_size_counts_only_the_road_region_and_saturates():
    assert size_score((0, 0, 1, 0.3)) == 0.0  # entirely above the road region (sky/buildings)
    assert size_score((0, 0.45, 1, 1)) == 1.0
    small = size_score((0.45, 0.8, 0.55, 0.9))
    assert 0 < small < 0.2


def test_big_central_pothole_is_dangerous_and_side_crack_is_minor():
    pothole = Detection(DamageClass.pothole, 0.9, (0.3, 0.55, 0.7, 0.95))
    r = score_detection(pothole, depth=0.9)
    assert r.label == SeverityLabel.dangerous
    assert reason(r) == "large, looks deep and in the wheel path"

    crack = Detection(DamageClass.crack_along, 0.6, (0.02, 0.7, 0.08, 0.95))
    r2 = score_detection(crack, depth=0.1)
    assert r2.label == SeverityLabel.minor
    assert "near the road edge" in reason(r2)


def test_depth_score_detects_a_dip():
    inv = np.tile(np.linspace(1.0, 0.0, 200)[:, None], (1, 200)).astype(np.float32)  # road plane
    flat = depth_score(inv, (0.4, 0.6, 0.6, 0.8))
    hole = inv.copy()
    hole[120:160, 80:120] -= 0.08  # the floor of the pothole is further away
    deep = depth_score(hole, (0.4, 0.6, 0.6, 0.8))
    assert flat is not None and deep is not None
    assert flat < 0.15
    assert deep > 0.6


def test_depth_score_none_for_tiny_box():
    assert depth_score(np.zeros((100, 100), np.float32), (0.5, 0.5, 0.505, 0.505)) is None
