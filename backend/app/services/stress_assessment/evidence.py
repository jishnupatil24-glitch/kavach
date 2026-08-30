"""
Evidence assembly and the detection gate for one problem category on
one day. Consumes Phase 3's ALREADY-COMPUTED ParameterAnalysis
(current/trend/persistence/icar) -- never recomputes trend, rate,
persistence, or ICAR deviation itself.

DETECTION GATE (approved, no additional invented thresholds):

    adverse_trend_matched  = trend.direction == category.adverse_trend
    persistence_exists     = persistence.days is not None
    icar_deviation_adverse = sign(icar.signed_difference) == category.adverse_icar_sign

    if trend.direction == "UNDETERMINED":              status = insufficient_data
    elif not (adverse_trend_matched and persistence_exists and icar_deviation_adverse):
                                                         status = no_evidence
    elif sourced corroboration available AND matched:   status = corroborated_evidence
    else:                                                status = weak_evidence

Every input to this gate already existed before Phase 4 (Phase 3's own
statistics, or a Phase 1 `status="sourced"` row) -- nothing here is a
newly invented magnitude cutoff or day-count.

HUMIDITY EXCEPTION (`humidity_low`/`humidity_high` only, approved
correction): these two categories have a real sourced numeric boundary
(`humidity_min_pct`/`humidity_max_pct`), unlike the 7 categories the
gate above was designed for. For these two, status is driven ENTIRELY
by `_humidity_range_corroboration`'s `boundary_ratio` -- the generic
trend/persistence/ICAR-sign proxy above is NOT consulted for status at
all, because it was found able to produce `weak_evidence` (which a
downstream eligibility gate could then act on) even when the sourced
boundary was never crossed (e.g. 73.63% humidity flagged
`humidity_low` against a 50% boundary). `trend.direction ==
"UNDETERMINED"` still yields `insufficient_data` first, same as every
other category -- that reflects Phase 3 data absence, not category-
specific evidence:

    boundary_ratio == 0.0        -> no_evidence
    0.0 < boundary_ratio < 1.0   -> weak_evidence
    boundary_ratio == 1.0        -> corroborated_evidence

See `_humidity_range_corroboration`'s own docstring for what
`boundary_ratio` means and why (Shamshiri et al. 2018's own notes
describe the two ends of each sourced range as distinct calibration
points, not one number under dispute).

SEVERITY (see _compute_severity below) is a SEPARATE, INDEPENDENT
field from `status` above -- "how serious is the observed pattern",
not "how strong is the evidence that it matches this category".
`weak_evidence` + `CRITICAL` severity and `corroborated_evidence` +
`LOW` severity are both valid, expected combinations. See
SEVERITY_DISCLAIMER: severity is a deterministic observational/
analytical score, never itself an agronomic diagnosis, and its band
boundaries are analytical conventions, not sourced agronomic
thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agronomic_parameter import AgronomicParameter
from app.models.sensor_observation import SensorObservation
from app.services.state_analysis.service import ParameterAnalysis
from app.services.stress_assessment.abnormal_duration import (
    AbnormalDurationResult,
    NO_RUN_CONTEXT_NOTE,
    classify_tier,
    compute_abnormal_duration,
)

STATUS_INSUFFICIENT_DATA = "insufficient_data"
STATUS_NO_EVIDENCE = "no_evidence"
STATUS_WEAK_EVIDENCE = "weak_evidence"
STATUS_CORROBORATED_EVIDENCE = "corroborated_evidence"

SEVERITY_INSUFFICIENT_DATA = "insufficient_data"
SEVERITY_LOW = "LOW"
SEVERITY_MODERATE = "MODERATE"
SEVERITY_HIGH = "HIGH"
SEVERITY_CRITICAL = "CRITICAL"

SEVERITY_DISCLAIMER = (
    "Severity is a deterministic observational/analytical severity score "
    "derived from Phase 3 signals. It is not itself an agronomic diagnosis "
    "and its band boundaries are not sourced agronomic thresholds."
)
"""
Approved verbatim wording -- must be surfaced in code, API output, CLI
output, and project documentation exactly as given, per the Phase 4
severity approval.
"""


@dataclass(frozen=True)
class RawRangeNote:
    """
    Descriptive-only summary of the analysis day's raw 6-hour
    sensor_observations for one field. NEVER used as an independent
    stress signal or fed into the detection gate above -- purely
    contextual, and labelled as such wherever it is displayed.
    """
    min_value: float
    max_value: float
    n_readings: int
    label: str = "Descriptive raw sensor range -- not used as an independent stress signal."


@dataclass(frozen=True)
class SeverityFactors:
    """
    The 3 self-calibrated, unit-free ratios severity is built from, and
    the 0/1/2 score each contributed. Always present together, or not
    at all (severity is "insufficient_data" with factors=None) -- see
    _compute_severity's docstring for the exact bands and why they are
    an ANALYTICAL convention, never an agronomic threshold.
    """
    deviation_ratio: float
    deviation_score: int
    intensity_ratio: float | None  # None only in the stable_band==0 special case (see below)
    intensity_score: int
    duration_fraction: float
    duration_score: int
    total_score: int


@dataclass(frozen=True)
class ProblemAssessment:
    category: str
    label: str
    field: str
    status: str  # insufficient_data | no_evidence | weak_evidence | corroborated_evidence
    direction: str  # Phase 3's own trend.direction, verbatim
    current_value: float
    icar_value: float | None
    icar_deviation: float | None
    rate_per_day: float | None
    rate_unit: str
    persistence_days: int | None
    sourced_corroboration_notes: list[str]
    provenance_notes: list[str]
    raw_range: RawRangeNote | None
    severity: str  # insufficient_data | LOW | MODERATE | HIGH | CRITICAL -- INDEPENDENT of `status` above
    severity_factors: SeverityFactors | None
    severity_disclaimer: str
    # SEPARATE from persistence_days above (trend-step continuation, Phase 3,
    # unchanged). Answers "how many consecutive days has THIS CATEGORY been
    # in its own adverse state" -- see abnormal_duration.py.
    abnormal_state_duration: AbnormalDurationResult


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def compute_raw_range(observations: list[SensorObservation], field: str) -> RawRangeNote | None:
    values = [getattr(o, field) for o in observations if getattr(o, field) is not None]
    if not values:
        return None
    return RawRangeNote(min_value=min(values), max_value=max(values), n_readings=len(values))


def _temperature_critical_stress_corroboration(
    db: Session, crop: str, current_value: float
) -> tuple[bool, list[str]]:
    """
    Reports ALL 4 sourced cultivar-specific critical-temperature values
    honestly -- never picks one as the universal threshold, since no
    cultivar is configured for KAVACH. "Matched" (for the gate) means
    the current value has reached or exceeded AT LEAST ONE of them.
    """
    rows = (
        db.query(AgronomicParameter)
        .filter(
            AgronomicParameter.crop == crop,
            AgronomicParameter.parameter_name == "temperature_critical_stress_c",
            AgronomicParameter.status == "sourced",
        )
        .order_by(AgronomicParameter.id)
        .all()
    )
    if not rows:
        return False, []

    matched = any(current_value >= r.value_numeric for r in rows if r.value_numeric is not None)
    listing = ", ".join(f"{r.value_numeric}°C [{r.context}]" for r in rows)
    note = (
        f"{len(rows)} cultivar-specific critical-temperature values are available from "
        f"the agronomic knowledge base ({listing}). No cultivar is configured for this "
        "simulation, therefore none is selected as the authoritative threshold."
    )
    return matched, [note]


def _humidity_range_corroboration(
    db: Session, crop: str, parameter_name: str, current_value: float, low_band: bool
) -> tuple[float | None, list[str]]:
    """
    humidity_min_pct (30-50%) is the sourced LOW band; humidity_max_pct
    (80-100%) is the sourced HIGH band. Per this row's own `notes`
    (Shamshiri et al. 2018): for the low band, 30% is documented as a
    night-time FAILURE FLOOR and 50% as where the general OPTIMAL band
    starts -- two distinct calibration points, not literature
    disagreement over one number. The high band's notes are weaker
    (cites 85-90%/90% risk points that don't land exactly on the
    stored 80/100 edges) but the same two-point structure is the only
    non-fabricated way to use both stored numbers, so it is applied
    symmetrically: 80% = onset edge, 100% = the physical ceiling.

    Returns `boundary_ratio` in [0, 1], NOT a matched/unmatched bool:

        0.0            current is at/beyond this band's own OPTIMAL-side
                       edge (50% for low, 80% for high) -- no evidence
        (0.0, 1.0)     between the optimal edge and the band's own far
                       edge -- weak evidence, scaled by how far in
        1.0            current has reached/passed the band's own far
                       edge (30% for low, 100% for high) -- corroborated

    Returns (None, []) if the sourced row is unavailable (defensive;
    both rows are always seeded in this project's DB) -- callers must
    treat None the same as 0.0 (no evidence), never as a match.
    """
    row = (
        db.query(AgronomicParameter)
        .filter(
            AgronomicParameter.crop == crop,
            AgronomicParameter.parameter_name == parameter_name,
            AgronomicParameter.status == "sourced",
        )
        .first()
    )
    if row is None or row.value_min is None or row.value_max is None or row.value_max == row.value_min:
        return None, []

    lo, hi = row.value_min, row.value_max
    if low_band:
        near_edge, far_edge = hi, lo  # 50 (optimal start), 30 (failure floor)
        raw_ratio = (hi - current_value) / (hi - lo)
    else:
        near_edge, far_edge = lo, hi  # 80 (onset), 100 (ceiling)
        raw_ratio = (current_value - lo) / (hi - lo)

    ratio = max(0.0, min(1.0, raw_ratio))

    if ratio <= 0.0:
        position = f"has not crossed this band's own optimal-side edge ({near_edge}%) -- no evidence from the sourced band"
    elif ratio >= 1.0:
        position = f"has reached or passed this band's own far edge ({far_edge}%) -- corroborated by the sourced band"
    else:
        position = f"is within this band's own sub-optimal zone ({lo}-{hi}%), boundary_ratio={ratio:.2f} -- weak evidence from the sourced band"

    note = (
        f"Sourced {parameter_name} range {lo}-{hi}% ({row.context}); "
        f"current value {current_value:.2f}% {position}."
    )
    return ratio, [note]


_CONTEXT_UNAVAILABLE_NOTES = {
    "water_depletion": "Soil field capacity / permanent wilting point are status=\"context_dependent\" (NULL) -- no sourced numeric moisture threshold exists; evidence is ICAR-deviation-based only.",
    "excessive_moisture": "Soil field capacity / permanent wilting point are status=\"context_dependent\" (NULL) -- no sourced numeric moisture threshold exists; evidence is ICAR-deviation-based only.",
    "temperature_deficit": "DAF Qld's temperature_min_c rows are sourced but linked only to day-less stages (no start_day/end_day) -- not applicable to a specific analysis day; evidence is ICAR-deviation-based only.",
    "nitrogen_related": "No sourced mg/kg soil-nitrogen threshold exists (only a kg/ha season total, unconvertible without a configured plant population); evidence is ICAR-deviation-based only.",
    "phosphorus_related": "No sourced mg/kg soil-phosphorus threshold exists (only a kg/ha season total, unconvertible without a configured plant population); evidence is ICAR-deviation-based only.",
    "potassium_related": "No sourced mg/kg soil-potassium threshold exists (only a kg/ha season total, unconvertible without a configured plant population); evidence is ICAR-deviation-based only.",
    "light_deficit": "A sourced dli_target_mol_m2_day range exists but only for the transplant/seedling stage, which has no day mapping -- cannot be verified applicable to the current analysis day; evidence is ICAR-deviation-based only.",
}


def _band_score(ratio: float, low: float, high: float) -> int:
    if ratio < low:
        return 0
    if ratio < high:
        return 1
    return 2


_SEVERITY_CATEGORY_BY_TOTAL_SCORE = {
    0: SEVERITY_LOW, 1: SEVERITY_LOW,
    2: SEVERITY_MODERATE, 3: SEVERITY_MODERATE,
    4: SEVERITY_HIGH, 5: SEVERITY_HIGH,
    6: SEVERITY_CRITICAL,
}


def _compute_severity(
    pa: ParameterAnalysis, boundary_ratio: float | None = None
) -> tuple[str, SeverityFactors | None]:
    """
    Three self-calibrated, unit-free ratios, each scored 0/1/2 via
    doubling bands anchored at their own natural "just significant"
    point -- an ANALYTICAL convention (documented, approved), never an
    agronomic fact:

      deviation_ratio  = |icar_deviation| / |icar_value|         bands: <0.10 / 0.10-0.30 / >=0.30
      intensity_ratio  = |rate_per_day| / trend.stable_band       bands: <2 / 2-4 / >=4
      duration_fraction= persistence.days / assessment_day        bands: <1/3 / 1/3-2/3 / >=2/3

    total_score (0-6) -> LOW/MODERATE/HIGH/CRITICAL. Computed with
    abs() throughout -- deliberately DIRECTION-AGNOSTIC, so two
    categories sharing a field (e.g. water_depletion/excessive_moisture)
    always get the SAME severity for the same day: severity describes
    how much this field is moving, not which direction is "adverse"
    for a particular category. That is intentional, not a bug.

    `boundary_ratio` (approved correction, `humidity_low`/`humidity_high`
    ONLY): when given, REPLACES the ICAR-based `deviation_ratio` above
    with `_humidity_range_corroboration`'s own [0,1] sourced-boundary
    ratio -- fed through the SAME existing 0.10/0.30 band_score, no new
    band invented. Before this, deviation_ratio for these two
    categories was computed from Phase 3's ICAR-reference deviation,
    which has nothing to do with distance from the sourced humidity
    boundary and could read near-zero right as the boundary was
    crossed. All other categories are unaffected -- `boundary_ratio`
    stays None and the ICAR-based formula below runs exactly as before.
    intensity_score/duration_score are untouched for every category,
    including humidity (unaffected by this correction; severity can
    still combine with status independently, per the module docstring).

    "insufficient_data" (factors=None) whenever ANY required Phase 3
    signal is unavailable: trend UNDETERMINED, persistence.days is
    None, or icar_value is None/zero (can't form a ratio against it) --
    unchanged by the boundary_ratio override, since intensity/duration
    still need these same Phase 3 signals.
    """
    trend = pa.trend
    persistence = pa.persistence
    icar = pa.icar

    if (
        trend.direction == "UNDETERMINED"
        or persistence.days is None
        or icar.icar_value is None
        or icar.icar_value == 0
        or icar.signed_difference is None
    ):
        return SEVERITY_INSUFFICIENT_DATA, None

    if boundary_ratio is not None:
        deviation_ratio = boundary_ratio
    else:
        deviation_ratio = abs(icar.signed_difference) / abs(icar.icar_value)
    deviation_score = _band_score(deviation_ratio, 0.10, 0.30)

    if trend.stable_band is None:
        # Cannot happen once trend.direction != "UNDETERMINED" (Phase 3
        # only leaves stable_band unset in the UNDETERMINED case,
        # already excluded above) -- guarded anyway rather than assumed.
        return SEVERITY_INSUFFICIENT_DATA, None
    if trend.stable_band == 0:
        # A perfectly noise-free window (zero residual variance): any
        # nonzero rate is unambiguously maximal intensity by
        # definition, not merely "undetermined" -- the ratio itself
        # (division by zero) isn't stored, but the score is still exact.
        intensity_ratio = None
        intensity_score = 2 if (trend.rate_per_day or 0) != 0 else 0
    else:
        intensity_ratio = abs(trend.rate_per_day or 0.0) / trend.stable_band
        intensity_score = _band_score(intensity_ratio, 2.0, 4.0)

    duration_fraction = persistence.days / pa.current.day
    duration_score = _band_score(duration_fraction, 1 / 3, 2 / 3)

    total_score = deviation_score + intensity_score + duration_score
    category = _SEVERITY_CATEGORY_BY_TOTAL_SCORE[total_score]

    return category, SeverityFactors(
        deviation_ratio=deviation_ratio,
        deviation_score=deviation_score,
        intensity_ratio=intensity_ratio,
        intensity_score=intensity_score,
        duration_fraction=duration_fraction,
        duration_score=duration_score,
        total_score=total_score,
    )


def compute_problem_assessment(
    db: Session,
    crop: str,
    category,  # ProblemCategory
    pa: ParameterAnalysis,
    raw_range: RawRangeNote | None,
    run_id: int | None = None,
) -> ProblemAssessment:
    current = pa.current
    trend = pa.trend
    persistence = pa.persistence
    icar = pa.icar

    corroboration_notes: list[str] = []
    provenance_notes: list[str] = []
    corroborated = False
    humidity_boundary_ratio: float | None = None
    is_humidity_category = category.key in ("humidity_low", "humidity_high")

    if category.key == "heat_related":
        corroborated, corroboration_notes = _temperature_critical_stress_corroboration(
            db, crop, current.value
        )
    elif category.key == "humidity_low":
        humidity_boundary_ratio, corroboration_notes = _humidity_range_corroboration(
            db, crop, "humidity_min_pct", current.value, low_band=True
        )
    elif category.key == "humidity_high":
        humidity_boundary_ratio, corroboration_notes = _humidity_range_corroboration(
            db, crop, "humidity_max_pct", current.value, low_band=False
        )
    elif category.key in _CONTEXT_UNAVAILABLE_NOTES:
        provenance_notes = [_CONTEXT_UNAVAILABLE_NOTES[category.key]]

    if trend.direction == "UNDETERMINED":
        status = STATUS_INSUFFICIENT_DATA
    elif is_humidity_category:
        # Approved correction: status here is driven ENTIRELY by the
        # sourced boundary ratio -- the generic trend/persistence/
        # ICAR-sign proxy below is never consulted for these two
        # categories (see module docstring's HUMIDITY EXCEPTION).
        ratio = humidity_boundary_ratio or 0.0
        if humidity_boundary_ratio is None or ratio <= 0.0:
            status = STATUS_NO_EVIDENCE
        elif ratio >= 1.0:
            status = STATUS_CORROBORATED_EVIDENCE
        else:
            status = STATUS_WEAK_EVIDENCE
    else:
        adverse_trend_matched = trend.direction == category.adverse_trend
        persistence_exists = persistence.days is not None
        icar_deviation_adverse = (
            icar.signed_difference is not None
            and _sign(icar.signed_difference) == category.adverse_icar_sign
        )
        gate = adverse_trend_matched and persistence_exists and icar_deviation_adverse

        if not gate:
            status = STATUS_NO_EVIDENCE
        elif corroborated:
            status = STATUS_CORROBORATED_EVIDENCE
        else:
            status = STATUS_WEAK_EVIDENCE

    severity, severity_factors = _compute_severity(
        pa, boundary_ratio=humidity_boundary_ratio if is_humidity_category else None
    )

    if db is not None and run_id is not None:
        abnormal_state_duration = compute_abnormal_duration(db, crop, category, run_id, current.day)
    else:
        abnormal_state_duration = AbnormalDurationResult(
            category.key, classify_tier(category.key), None, NO_RUN_CONTEXT_NOTE
        )

    return ProblemAssessment(
        category=category.key,
        label=category.label,
        field=category.field,
        status=status,
        direction=trend.direction,
        current_value=current.value,
        icar_value=icar.icar_value,
        icar_deviation=icar.signed_difference,
        rate_per_day=trend.rate_per_day,
        rate_unit=trend.rate_unit,
        persistence_days=persistence.days,
        sourced_corroboration_notes=corroboration_notes,
        provenance_notes=provenance_notes,
        raw_range=raw_range,
        severity=severity,
        severity_factors=severity_factors,
        severity_disclaimer=SEVERITY_DISCLAIMER,
        abnormal_state_duration=abnormal_state_duration,
    )
