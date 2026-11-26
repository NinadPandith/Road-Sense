"""B5: the 9-step report processing sequence (docs/app-flow.md, "Backend processing sequence").

Used by POST /reports (citizen photos and Drive-mode frames) and by the survey worker.
"""

import hashlib
import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

import numpy as np
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.models import Detection as DetectionRow
from app.models import Report
from app.models.enums import ReportSource, ReportStatus
from app.schemas.reports import BoxOut, ReportResult, Severity, SeverityFactors
from app.services import defects as defect_service
from app.services import geo, images, privacy
from app.services.classes import confidence_label
from app.services.codes import new_tracking_code
from app.services.depth import DepthEstimator, depth_score
from app.services.detect import Detection, Detector
from app.services.merge import Finding, MergeOutcome, merge_report, point_wkt
from app.services.settings import SettingsValues
from app.services.severity import SeverityResult, reason, score_detection
from app.services.storage import REPORT_IMAGES, Storage

log = logging.getLogger(__name__)


@dataclass
class Services:
    """Everything the pipeline needs from the outside world; replaced by fakes in tests."""

    get_detector: Callable[[], Detector]
    get_depth: Callable[[], DepthEstimator | None]
    storage: Storage
    road_lookup: Callable[[float, float], geo.RoadInfo]
    model_version: str


@dataclass
class ReportInput:
    lat: float
    lon: float
    captured_at: datetime
    source: ReportSource
    accuracy_m: float | None = None
    note: str | None = None
    client_report_id: uuid.UUID | None = None
    ip_hash: str | None = None
    survey_id: uuid.UUID | None = None


def hash_ip(ip: str, salt: str) -> str:
    return hashlib.sha256((ip + salt).encode()).hexdigest()


def check_rate_limit(
    db: Session, ip_hash: str | None, limit: int, source: ReportSource = ReportSource.citizen
) -> None:
    """Backend Schema query 2: at most `limit` reports per IP per hour, counted per source
    (a Drive-mode ride legitimately sends many frames; citizen photos stay at 10/hour)."""
    if not ip_hash:
        return
    count = db.execute(
        text(
            "select count(*) from reports where ip_hash = :h "
            "and source = cast(:src as report_source) "
            "and created_at > now() - interval '1 hour'"
        ),
        {"h": ip_hash, "src": source.value},
    ).scalar_one()
    if count >= limit:
        raise ApiError("rate_limited", 429, retry_after_s=3600)


def unique_tracking_code(db: Session) -> str:
    for attempt in range(12):
        code = new_tracking_code(4 if attempt < 6 else 5)
        if not db.scalar(select(func.count()).where(Report.tracking_code == code)):
            return code
    raise RuntimeError("could not find a free tracking code")


def store_images(storage: Storage, report: Report, rgb: np.ndarray, now: datetime) -> None:
    base = f"{now:%Y}/{now:%m}/{report.id}"
    report.image_path = f"{base}.jpg"
    report.thumb_path = f"{base}_thumb.jpg"
    storage.upload(REPORT_IMAGES, report.image_path, images.encode_jpeg(rgb), "image/jpeg")
    storage.upload(
        REPORT_IMAGES, report.thumb_path, images.encode_jpeg(rgb, images.THUMB_SIDE), "image/jpeg"
    )


def _scored(
    rgb: np.ndarray, dets: list[Detection], services: Services, settings: SettingsValues
) -> list[tuple[Detection, SeverityResult]]:
    inv_depth = None
    estimator = services.get_depth()
    if estimator is not None:
        try:
            inv_depth = estimator.predict(rgb)
        except Exception as exc:  # noqa: BLE001 - depth is optional (PRD fallback)
            log.warning("Depth estimation failed: %s", exc)
    out = []
    for d in dets:
        dep = depth_score(inv_depth, d.box) if inv_depth is not None else None
        out.append((d, score_detection(d, dep, settings)))
    return out


def build_result(
    report: Report,
    storage: Storage,
    outcome: str,
    merge: MergeOutcome | None = None,
    best: tuple[Detection, SeverityResult] | None = None,
    scored: list[tuple[Detection, SeverityResult]] | None = None,
) -> ReportResult:
    res = ReportResult(
        tracking_code=report.tracking_code,
        status=report.status,
        outcome=outcome,  # type: ignore[arg-type]
        defect_id=report.defect_id,
        thumb_url=storage.public_url(REPORT_IMAGES, report.thumb_path)
        if report.thumb_path
        else None,
        image_url=storage.public_url(REPORT_IMAGES, report.image_path)
        if report.image_path
        else None,
    )
    if merge:
        res.report_count = merge.defect.report_count
    if best:
        det, sev = best
        res.damage_class = det.damage_class
        res.confidence_label = confidence_label(det.confidence)  # type: ignore[assignment]
        res.severity = Severity(
            label=sev.label,
            score=round(sev.score, 2),
            factors=SeverityFactors(**sev.factors),
            reason=reason(sev),
        )
    if scored:
        res.boxes = [
            BoxOut(damage_class=d.damage_class, confidence=d.confidence, box=list(d.box))
            for d, _ in scored
        ]
    return res


def process_report(
    db: Session,
    services: Services,
    settings: SettingsValues,
    image_bytes: bytes,
    inp: ReportInput,
    max_per_hour: int,
) -> ReportResult:
    now = datetime.now(UTC)

    # Idempotency: the offline outbox may send the same report twice.
    if inp.client_report_id:
        existing = db.scalar(select(Report).where(Report.client_report_id == inp.client_report_id))
        if existing:
            return track_as_result(db, services, existing)

    # 1. Checks: pilot area, rate limit, file type.
    if not geo.in_pilot_area(inp.lat, inp.lon):
        raise ApiError("outside_pilot_area", 422)
    if inp.source != ReportSource.survey:
        check_rate_limit(db, inp.ip_hash, max_per_hour, inp.source)
    rgb = images.resize_max(images.load_image(image_bytes), images.MAX_SIDE)

    # 3 (before 2). Privacy: blur in memory; the original is never stored.
    rgb, _ = privacy.anonymise(rgb)
    if not images.measure_quality(rgb).ok:
        raise ApiError("image_too_dark", 422)

    return process_frame(db, services, settings, rgb, inp, now=now)


def process_frame(
    db: Session,
    services: Services,
    settings: SettingsValues,
    rgb: np.ndarray,
    inp: ReportInput,
    dets: list[Detection] | None = None,
    now: datetime | None = None,
) -> ReportResult:
    """Steps 2 and 4-9 for an image that is already blurred and checked.

    The survey worker passes `dets` it has already computed, so frames are not detected twice.
    """
    now = now or datetime.now(UTC)

    # 2. Report row.
    report = Report(
        tracking_code=unique_tracking_code(db),
        client_report_id=inp.client_report_id,
        source=inp.source,
        status=ReportStatus.processing,
        survey_id=inp.survey_id,
        location=point_wkt(inp.lat, inp.lon),
        gps_accuracy_m=inp.accuracy_m,
        captured_at=inp.captured_at,
        note=(inp.note or None),
        ip_hash=inp.ip_hash,
        model_version=services.model_version,
    )
    db.add(report)
    db.flush()

    # 4. Detect.
    if dets is None:
        dets = services.get_detector().detect(rgb, settings.min_confidence)
    if not dets:
        report.status = ReportStatus.no_damage
        if inp.source == ReportSource.citizen:  # kept so "Send anyway" can go to review
            store_images(services.storage, report, rgb, now)
        db.flush()
        return build_result(report, services.storage, "no_damage")

    store_images(services.storage, report, rgb, now)

    # 5. Score each box and save detections.
    scored = _scored(rgb, dets, services, settings)
    for det, sev in scored:
        db.add(
            DetectionRow(
                report_id=report.id,
                damage_class=det.damage_class,
                confidence=det.confidence,
                box=list(det.box),
                size_score=sev.size,
                depth_score=sev.depth,
                type_score=sev.type,
                position_score=sev.position,
                severity_score=sev.score,
                severity_label=sev.label,
                model_version=services.model_version,
            )
        )
    best = max(scored, key=lambda x: x[1].score)

    # 6. Merge with a defect within the merge radius, or create one.
    finding = Finding(best[0].damage_class, best[1].score, best[1].label)
    merge = merge_report(db, report, inp.lat, inp.lon, finding, settings, now)

    # 7. Enrich new defects. 8. Prioritise.
    if merge.is_new:
        defect_service.enrich(db, merge.defect, settings, services.road_lookup)
    defect_service.recalculate(db, merge.defect, settings, now)

    report.status = ReportStatus.done
    db.flush()
    # 9. Respond.
    return build_result(
        report, services.storage, "new" if merge.is_new else "merged", merge, best, scored
    )


def send_anyway(
    db: Session, services: Services, settings: SettingsValues, report: Report
) -> ReportResult:
    """Citizen disagrees with 'no damage': the report goes to an engineer as Needs review."""
    if report.status != ReportStatus.no_damage:
        return track_as_result(db, services, report)
    lat, lon = db.execute(
        text("select ST_Y(location::geometry), ST_X(location::geometry) from reports where id=:i"),
        {"i": report.id},
    ).one()
    now = datetime.now(UTC)
    merge = merge_report(db, report, lat, lon, Finding(None, None, None), settings, now)
    if merge.is_new:
        defect_service.enrich(db, merge.defect, settings, services.road_lookup)
    defect_service.recalculate(db, merge.defect, settings, now)
    report.status = ReportStatus.needs_review
    db.flush()
    return build_result(report, services.storage, "needs_review", merge)


def track_as_result(db: Session, services: Services, report: Report) -> ReportResult:
    """Rebuild a ReportResult for an already-processed report (idempotent retries)."""
    from app.models import Defect

    outcome = {
        ReportStatus.no_damage: "no_damage",
        ReportStatus.needs_review: "needs_review",
        ReportStatus.processing: "processing",
        ReportStatus.failed: "processing",
    }.get(report.status, "merged")
    res = build_result(report, services.storage, outcome)
    if report.defect_id:
        defect = db.get(Defect, report.defect_id)
        if defect:
            res.report_count = defect.report_count
            if outcome == "merged" and defect.report_count == 1:
                res.outcome = "new"
    dets = db.scalars(
        select(DetectionRow)
        .where(DetectionRow.report_id == report.id)
        .order_by(DetectionRow.severity_score.desc())
    ).all()
    if dets:
        top = dets[0]
        res.damage_class = top.damage_class
        res.confidence_label = confidence_label(top.confidence)  # type: ignore[assignment]
        sev = SeverityResult(
            size=top.size_score,
            depth=top.depth_score,
            type=top.type_score,
            position=top.position_score,
            score=top.severity_score,
            label=top.severity_label,
        )
        res.severity = Severity(
            label=sev.label,
            score=round(sev.score, 2),
            factors=SeverityFactors(**sev.factors),
            reason=reason(sev),
        )
        res.boxes = [
            BoxOut(damage_class=d.damage_class, confidence=d.confidence, box=list(d.box))
            for d in dets
        ]
    return res
