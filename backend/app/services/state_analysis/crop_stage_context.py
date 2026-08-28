"""
Crop-stage and agronomic-context resolution against the EXISTING
Phase 1/1.5C `crop_stages` / `agronomic_parameters` tables. No new
stage taxonomy, no new agronomic constants -- this module only reads.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agronomic_parameter import AgronomicParameter
from app.models.crop_stage import CropStage


@dataclass(frozen=True)
class StageMatch:
    stage_id: int
    name: str
    start_day: int
    end_day: int
    source_id: int | None


@dataclass(frozen=True)
class AgronomicContextItem:
    parameter_name: str
    domain: str
    value_display: str
    unit: str | None
    status: str
    source_id: int | None
    context: str | None
    notes: str | None


def resolve_crop_stages(db: Session, crop: str, day: int) -> list[StageMatch]:
    """
    Only stages with a real (non-NULL) start_day/end_day can be matched
    by day -- e.g. the DAF Qld phenological stages (germination, etc.)
    have no day mapping in the source data and are never matched here,
    rather than guessed.

    If more than one day-mapped stage's range contains `day` (e.g. day
    100, where kc_mid_stage's sourced range ends and kc_late_stage's
    sourced range begins -- both boundaries are inclusive in the
    source-derived data, a real overlap already present in Sharma &
    Changade 2025's own table, not invented here), ALL matches are
    returned -- never silently narrowed to one.
    """
    rows = (
        db.query(CropStage)
        .filter(
            CropStage.crop == crop,
            CropStage.start_day.isnot(None),
            CropStage.end_day.isnot(None),
            CropStage.start_day <= day,
            CropStage.end_day >= day,
        )
        .order_by(CropStage.id)
        .all()
    )
    return [StageMatch(r.id, r.name, r.start_day, r.end_day, r.source_id) for r in rows]


def _format_value(p: AgronomicParameter) -> str:
    if p.value_numeric is not None:
        return str(p.value_numeric)
    if p.value_min is not None and p.value_max is not None:
        return f"{p.value_min}-{p.value_max}"
    if p.value_text is not None:
        return p.value_text
    return f"(no value -- status: {p.status})"


def resolve_agronomic_context(db: Session, crop: str, stage_ids: list[int]) -> list[AgronomicContextItem]:
    """
    Agronomic parameters tied to one of the resolved (day-mapped) crop
    stages above -- e.g. Kc values for a matched Kc stage. Parameters
    with no stage_id (general, not stage-specific -- humidity bounds,
    DLI target, soil pH, nutrient totals, etc.) are intentionally NOT
    included here: this section is context for the CURRENT stage
    specifically, not a dump of every agronomic fact in the DB.
    """
    if not stage_ids:
        return []
    rows = (
        db.query(AgronomicParameter)
        .filter(AgronomicParameter.crop == crop, AgronomicParameter.stage_id.in_(stage_ids))
        .order_by(AgronomicParameter.id)
        .all()
    )
    return [
        AgronomicContextItem(
            parameter_name=r.parameter_name,
            domain=r.domain,
            value_display=_format_value(r),
            unit=r.unit,
            status=r.status,
            source_id=r.source_id,
            context=r.context,
            notes=r.notes,
        )
        for r in rows
    ]
