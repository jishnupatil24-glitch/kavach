"""
Abnormal-state duration: a SEPARATE concept from Phase 3's own
`persistence_days` (trend-step continuation -- see
app.services.state_analysis.persistence, UNCHANGED by this module).

This module answers a different question: "how many consecutive days,
walking backward from the assessment day, has THIS CATEGORY already
been in its own adverse state" -- derived entirely from already-
persisted Phase 3 `state_analysis_history` rows. Never recomputes
trend/rate/ICAR-deviation itself, never imports persistence.py or
trend.py, and never writes to Phase 3's history.

Two tiers, per the approved design:

TIER 1 -- sourced-threshold categories (heat_related, humidity_low,
humidity_high): a real, day-independent, independently sourced numeric
boundary exists in AgronomicParameter (status="sourced"). A day counts
as abnormal when that day's Phase 3 daily-aggregated CURRENT value
crosses the boundary -- the same boundary numbers
app.services.stress_assessment.evidence's own corroboration functions
already use for the single assessment day, applied here across every
stored day instead of just one.

TIER 2 -- no sourced threshold exists (water_depletion,
excessive_moisture, temperature_deficit, nitrogen_related,
phosphorus_related, potassium_related, light_deficit): confirmed by
direct query against the actual agronomic_parameters table -- soil
field capacity/permanent wilting point are context_dependent/NULL,
DAF Qld temperature_min/max are tied to day-less crop stages (no
start_day/end_day), N/P/K are sourced only as kg/ha season totals
(unconvertible without a configured plant population), and DLI is
sourced only for an unmapped seedling stage. The only legitimate
signal left is Phase 3's own per-day trend direction and ICAR-
deviation sign. A day counts as abnormal only when BOTH already-stored
Phase 3 signals for that day agree with the category's own adverse
direction (category.adverse_trend / category.adverse_icar_sign from
categories.py -- never a magnitude cutoff invented here).

Sign alone was tested against the real excess_irrigation run (run_id=2)
during design and found to overcount noise: ICAR-deviation sign for
excessive_moisture was already positive from day 14 (25 days before
day 38), including an 11-day span (days 14-26) at 0.03-0.36 percentage
points of deviation -- indistinguishable from sensor noise. Requiring
the day's trend direction to also agree with the category removes that
false-positive tail without inventing any new magnitude threshold:
trend was FALLING for that field through day 29 and only turned RISING
at day 30, so the combined predicate starts the count there instead.

Every Tier 2 result carries an explicit provenance note distinguishing
it from a sourced threshold -- see TIER2_PROVENANCE_NOTE.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agronomic_parameter import AgronomicParameter
from app.models.state_analysis_history import StateAnalysisHistory
from app.services.stress_assessment.categories import ProblemCategory

TIER_SOURCED_THRESHOLD = "sourced_threshold"
TIER_ICAR_SIGN_TREND_PROXY = "icar_sign_trend_proxy"

TIER2_PROVENANCE_NOTE = (
    "This is an ICAR-deviation-sign + trend-direction proxy, NOT a sourced "
    "agronomic threshold -- no sourced numeric threshold exists for this "
    "category in the current agronomic dataset."
)

NO_RUN_CONTEXT_NOTE = (
    "No run/day context was provided to compute_problem_assessment -- "
    "abnormal-state duration was not computed."
)

_TIER1_CATEGORIES = {"heat_related", "humidity_low", "humidity_high"}


@dataclass(frozen=True)
class AbnormalDurationResult:
    category: str
    tier: str  # TIER_SOURCED_THRESHOLD | TIER_ICAR_SIGN_TREND_PROXY
    days: int | None
    provenance_note: str


def classify_tier(category_key: str) -> str:
    return TIER_SOURCED_THRESHOLD if category_key in _TIER1_CATEGORIES else TIER_ICAR_SIGN_TREND_PROXY


def _sign(x: float) -> int:
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0


def _sourced_threshold(db: Session, crop: str, category_key: str) -> tuple[float, str] | None:
    """
    Reuses the exact boundary numbers app.services.stress_assessment
    .evidence's own corroboration functions read for the assessment
    day -- never a separately invented threshold.
    """
    if category_key == "heat_related":
        rows = (
            db.query(AgronomicParameter)
            .filter(
                AgronomicParameter.crop == crop,
                AgronomicParameter.parameter_name == "temperature_critical_stress_c",
                AgronomicParameter.status == "sourced",
            )
            .all()
        )
        values = [r.value_numeric for r in rows if r.value_numeric is not None]
        if not values:
            return None
        threshold = min(values)
        return threshold, (
            f"current value >= {threshold}°C (the lowest of {len(values)} sourced "
            "cultivar-specific critical-temperature values -- 'abnormal' means at or above "
            "the most conservative sourced figure)"
        )

    if category_key in ("humidity_low", "humidity_high"):
        parameter_name = "humidity_min_pct" if category_key == "humidity_low" else "humidity_max_pct"
        row = (
            db.query(AgronomicParameter)
            .filter(
                AgronomicParameter.crop == crop,
                AgronomicParameter.parameter_name == parameter_name,
                AgronomicParameter.status == "sourced",
            )
            .first()
        )
        if row is None or row.value_min is None or row.value_max is None:
            return None
        if category_key == "humidity_low":
            boundary = row.value_max
            return boundary, f"current value <= {boundary}% (sourced {parameter_name} band's own upper edge)"
        boundary = row.value_min
        return boundary, f"current value >= {boundary}% (sourced {parameter_name} band's own lower edge)"

    return None


def _day_entry(parameters_json: str, field: str) -> dict | None:
    for entry in json.loads(parameters_json):
        if entry["current"]["field"] == field:
            return entry
    return None


def compute_abnormal_duration(
    db: Session, crop: str, category: ProblemCategory, run_id: int, upto_day: int
) -> AbnormalDurationResult:
    """
    Walks backward from `upto_day` over already-persisted
    state_analysis_history rows for this run, counting consecutive
    days that satisfy this category's own abnormal-state test. Stops
    at the first day that fails the test, or at the first day missing
    from history (a gap is never assumed abnormal or normal).
    """
    rows = (
        db.query(StateAnalysisHistory.day, StateAnalysisHistory.parameters_json)
        .filter(StateAnalysisHistory.simulation_run_id == run_id, StateAnalysisHistory.day <= upto_day)
        .order_by(StateAnalysisHistory.day)
        .all()
    )
    by_day = {day: _day_entry(pj, category.field) for day, pj in rows}

    tier = classify_tier(category.key)

    if tier == TIER_SOURCED_THRESHOLD:
        threshold_info = _sourced_threshold(db, crop, category.key)
        if threshold_info is None:
            return AbnormalDurationResult(
                category.key, tier, None,
                "No sourced threshold available for this category -- abnormal-state duration cannot be computed.",
            )
        boundary, description = threshold_info
        note = f"Sourced-threshold abnormal state: {description}."

        def is_abnormal(entry: dict) -> bool:
            value = entry["current"]["value"]
            if category.key == "humidity_low":
                return value <= boundary
            return value >= boundary  # heat_related, humidity_high

    else:
        note = TIER2_PROVENANCE_NOTE

        def is_abnormal(entry: dict) -> bool:
            trend_ok = entry["trend"]["direction"] == category.adverse_trend
            diff = entry["icar"]["signed_difference"]
            icar_ok = diff is not None and _sign(diff) == category.adverse_icar_sign
            return trend_ok and icar_ok

    if by_day.get(upto_day) is None:
        return AbnormalDurationResult(
            category.key, tier, None,
            "No Phase 3 history recorded for this day -- abnormal-state duration cannot be assessed.",
        )

    count = 0
    d = upto_day
    while by_day.get(d) is not None and is_abnormal(by_day[d]):
        count += 1
        d -= 1

    return AbnormalDurationResult(category.key, tier, count, note)
