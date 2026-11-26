"""M8: severity score per detection (docs/PRD.md, "Severity score").

    S = wA*A + wD*D + wT*T + wP*P      (v1 weights 0.35, 0.35, 0.20, 0.10)

A size      box area / road area in the frame (v1 road area = fixed lower-frame region)
D depth     relative depth drop inside the box vs. the road around it (services/depth.py)
T type      pothole 1.0, alligator 0.7, across 0.5, along 0.4
P position  1.0 near the lane centre, falling to 0.3 at the frame edge

If D is unavailable the remaining weights are rescaled to sum to 1 (PRD: "fall back to size +
type"), so a missing depth model never pushes every score down.
"""

from dataclasses import dataclass

from app.models.enums import DamageClass, SeverityLabel
from app.services.detect import Detection
from app.services.settings import DEFAULT_SETTINGS, SettingsValues

# v1 road region: the lower part of the frame, where the road is in a phone/dashcam photo.
ROAD_TOP = 0.45
ROAD_AREA = 1.0 - ROAD_TOP
# A box covering this share of the road region already counts as maximum size.
# A calibration constant: tune in experiment E3.
FULL_SIZE_SHARE = 0.20
# P: flat 1.0 within this distance of the centre line, then linear down to EDGE_POSITION.
CENTRE_PLATEAU = 0.2
EDGE_POSITION = 0.3


@dataclass(frozen=True)
class SeverityResult:
    size: float
    depth: float | None
    type: float
    position: float
    score: float
    label: SeverityLabel

    @property
    def factors(self) -> dict[str, float | None]:
        return {
            "size": round(self.size, 2),
            "depth": None if self.depth is None else round(self.depth, 2),
            "type": round(self.type, 2),
            "position": round(self.position, 2),
        }


def size_score(box: tuple[float, float, float, float]) -> float:
    x1, y1, x2, y2 = box
    y1c = max(y1, ROAD_TOP)
    in_road = max(0.0, x2 - x1) * max(0.0, y2 - y1c)
    return min(1.0, (in_road / ROAD_AREA) / FULL_SIZE_SHARE)


def position_score(centre_x: float) -> float:
    d = min(1.0, abs(centre_x - 0.5) / 0.5)
    if d <= CENTRE_PLATEAU:
        return 1.0
    t = (d - CENTRE_PLATEAU) / (1.0 - CENTRE_PLATEAU)
    return 1.0 - t * (1.0 - EDGE_POSITION)


def type_score(damage_class: DamageClass, settings: SettingsValues = DEFAULT_SETTINGS) -> float:
    return settings.type_weights[damage_class.value]


def label_for(score: float, settings: SettingsValues = DEFAULT_SETTINGS) -> SeverityLabel:
    if score >= settings.thresholds.dangerous:
        return SeverityLabel.dangerous
    if score >= settings.thresholds.moderate:
        return SeverityLabel.moderate
    return SeverityLabel.minor


def combine(
    size: float,
    depth: float | None,
    type_: float,
    position: float,
    settings: SettingsValues = DEFAULT_SETTINGS,
) -> float:
    w = settings.severity_weights
    if depth is None:
        total = w.A + w.T + w.P
        s = (w.A * size + w.T * type_ + w.P * position) / total
    else:
        s = w.A * size + w.D * depth + w.T * type_ + w.P * position
    return float(min(1.0, max(0.0, s)))


def score_detection(
    det: Detection,
    depth: float | None,
    settings: SettingsValues = DEFAULT_SETTINGS,
) -> SeverityResult:
    a = size_score(det.box)
    t = type_score(det.damage_class, settings)
    p = position_score(det.centre_x)
    s = round(combine(a, depth, t, p, settings), 4)
    return SeverityResult(size=a, depth=depth, type=t, position=p, score=s, label=label_for(s))


def reason(result: SeverityResult) -> str:
    """Plain-words reason from the strongest factors: 'large, deep and in the wheel path'."""
    parts: list[str] = []
    if result.size >= 0.6:
        parts.append("large")
    elif result.size < 0.25:
        parts.append("small")
    if result.depth is not None:
        if result.depth >= 0.6:
            parts.append("looks deep")
        elif result.depth < 0.25:
            parts.append("looks shallow")
    parts.append("in the wheel path" if result.position >= 0.8 else "near the road edge")
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]
