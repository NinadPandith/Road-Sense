"""B8: repair priority (docs/PRD.md, "Repair priority").

Priority = S x R x (1 + 0.1 min(n, 10)) x (1 + 0.02 min(t, 30)) x B
"""

from dataclasses import dataclass
from datetime import datetime

from app.models.enums import RoadClass, SeverityLabel
from app.services.settings import DEFAULT_SETTINGS, SettingsValues


@dataclass(frozen=True)
class PriorityResult:
    priority: float
    terms: dict


def days_open(first_reported_at: datetime, now: datetime) -> int:
    return max(0, (now - first_reported_at).days)


def compute_priority(
    severity: float | None,
    road_class: RoadClass,
    report_count: int,
    days: int,
    near_sensitive: bool,
    settings: SettingsValues = DEFAULT_SETTINGS,
) -> PriorityResult:
    s = severity or 0.0
    r = settings.road_weights.get(road_class.value, settings.road_weights["unknown"])
    n, t = report_count, days
    b = settings.sensitive_boost if near_sensitive else 1.0
    p = s * r * (1 + 0.1 * min(n, 10)) * (1 + 0.02 * min(t, 30)) * b
    terms = {"S": round(s, 2), "R": r, "n": n, "t": t, "B": b}
    return PriorityResult(priority=round(p, 4), terms=terms)


ROAD_WORDS = {
    RoadClass.major: "main road",
    RoadClass.secondary: "secondary road",
    RoadClass.tertiary: "local road",
    RoadClass.residential: "residential street",
    RoadClass.unknown: None,
}


def priority_reason(
    severity_label: SeverityLabel | None,
    road_class: RoadClass,
    sensitive_kind: str | None,
    report_count: int,
    days: int,
) -> str:
    """'Dangerous · main road · near school · 6 reports · 12 days open' (Content Guidelines)."""
    parts: list[str] = []
    if severity_label:
        parts.append(severity_label.value.capitalize())
    if road := ROAD_WORDS[road_class]:
        parts.append(road)
    if sensitive_kind:
        parts.append(f"near {sensitive_kind}")
    parts.append(f"{report_count} report" + ("" if report_count == 1 else "s"))
    parts.append(f"{days} day{'' if days == 1 else 's'} open")
    return " · ".join(parts)
