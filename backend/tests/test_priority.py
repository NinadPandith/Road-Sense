"""B8: priority formula against hand calculations."""

import pytest

from app.models.enums import RoadClass, SeverityLabel
from app.services.priority import compute_priority, priority_reason


@pytest.mark.parametrize(
    ("s", "road", "n", "t", "near", "expected"),
    [
        # S x R x (1 + 0.1 min(n,10)) x (1 + 0.02 min(t,30)) x B
        (0.82, RoadClass.major, 6, 12, True, 0.82 * 1.0 * 1.6 * 1.24 * 1.3),
        (0.50, RoadClass.residential, 1, 0, False, 0.50 * 0.4 * 1.1 * 1.0 * 1.0),
        (0.70, RoadClass.secondary, 25, 45, False, 0.70 * 0.8 * 2.0 * 1.6 * 1.0),  # both capped
        (0.30, RoadClass.unknown, 2, 5, True, 0.30 * 0.5 * 1.2 * 1.1 * 1.3),
        (0.95, RoadClass.tertiary, 10, 30, False, 0.95 * 0.6 * 2.0 * 1.6 * 1.0),
    ],
)
def test_priority_matches_hand_calculation(s, road, n, t, near, expected):
    result = compute_priority(s, road, n, t, near)
    assert result.priority == pytest.approx(expected, abs=1e-4)
    assert result.terms["n"] == n and result.terms["t"] == t


def test_needs_review_without_severity_has_zero_priority():
    assert compute_priority(None, RoadClass.major, 3, 4, False).priority == 0


def test_reason_reads_like_content_guidelines():
    assert (
        priority_reason(SeverityLabel.dangerous, RoadClass.major, "school", 6, 12)
        == "Dangerous · main road · near school · 6 reports · 12 days open"
    )
    assert priority_reason(None, RoadClass.unknown, None, 1, 1) == "1 report · 1 day open"
