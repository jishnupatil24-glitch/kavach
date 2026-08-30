"""
Reads Phase 6's approved project-defined optimization parameters from
the EXISTING agronomic_parameters table (status="project_defined") --
no new table, same query shape as Phase 5's own
app.services.decision_engine.config_parameters.

Every value here is KAVACH prototype optimization configuration, never
an externally sourced agronomic fact -- see PROJECT_DEFINED_DISCLAIMER.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agronomic_parameter import AgronomicParameter

DOMAIN_OPERATIONAL = "operational"
STATUS_PROJECT_DEFINED = "project_defined"

PROJECT_DEFINED_DISCLAIMER = (
    "KAVACH project-defined prototype optimization parameter -- not an "
    "externally sourced agronomic fact."
)

# Irrigation baseline, by approved Kc stage (L/plant/day, theoretical crop
# water requirement -- NOT delivered/irrigation-system volume).
PARAM_BASELINE_IRRIGATION_KC_INITIAL = "baseline_irrigation_kc_initial_l_per_plant_day"
PARAM_BASELINE_IRRIGATION_KC_MID = "baseline_irrigation_kc_mid_l_per_plant_day"
PARAM_BASELINE_IRRIGATION_KC_LATE = "baseline_irrigation_kc_late_l_per_plant_day"

BASELINE_IRRIGATION_PARAM_BY_STAGE_NAME: dict[str, str] = {
    "kc_initial_stage": PARAM_BASELINE_IRRIGATION_KC_INITIAL,
    "kc_mid_stage": PARAM_BASELINE_IRRIGATION_KC_MID,
    "kc_late_stage": PARAM_BASELINE_IRRIGATION_KC_LATE,
}
"""
Deliberately does NOT cover `kc_development_stage` (27-62 DAS) --
only the 3 stages explicitly approved for a project-defined baseline
value. A day resolving only to kc_development_stage produces
baseline=UNAVAILABLE with an explicit note, never a guessed number.
"""

# Severity -> adjustment magnitude (irrigation and nutrients share the
# same approved 10/20/30/40 scale, kept as separate parameter names per
# domain so either could be tuned independently later without touching
# the other).
IRRIGATION_ADJUSTMENT_PARAM_BY_SEVERITY: dict[str, str] = {
    "LOW": "irrigation_adjustment_pct_low",
    "MODERATE": "irrigation_adjustment_pct_moderate",
    "HIGH": "irrigation_adjustment_pct_high",
    "CRITICAL": "irrigation_adjustment_pct_critical",
}
NUTRIENT_ADJUSTMENT_PARAM_BY_SEVERITY: dict[str, str] = {
    "LOW": "nutrient_adjustment_pct_low",
    "MODERATE": "nutrient_adjustment_pct_moderate",
    "HIGH": "nutrient_adjustment_pct_high",
    "CRITICAL": "nutrient_adjustment_pct_critical",
}

PARAM_REVIEW_CYCLE_DAYS = "irrigation_review_cycle_days"
"""
A review/re-evaluation cadence, reused as the general Phase 6
intervention-duration figure for every quantitative action (irrigation
and nutrients alike) -- only one review-cycle value was approved, so
it is not duplicated per domain. NOT a claim that crop physiology
recovers in exactly this many days -- see effectiveness.py.
"""

IRRIGATION_EFFICIENCY_PARAM_BY_SYSTEM_TYPE: dict[str, str] = {
    "drip": "irrigation_efficiency_drip_pct",
    "sprinkler": "irrigation_efficiency_sprinkler_pct",
    "flood": "irrigation_efficiency_flood_pct",
}
PARAM_IRRIGATION_EFFICIENCY_UNKNOWN_DEFAULT = "irrigation_efficiency_unknown_default_pct"

PARAM_TYPICAL_APPLICATION_MULTIPLIER_PCT = "typical_application_multiplier_pct"
"""
Farmer-facing comparison point only: how much MORE water a farmer
typically applies than the theoretical crop requirement (baseline), in
the absence of a decision-support tool. This is a flat prototype
heuristic (same "simple, testable, not a fitted model" spirit as
irrigation_adjustment_pct_*) -- KAVACH has no sourced/measured farmer
irrigation-behavior dataset, so this stays project_defined, never
sourced, and is used only to give "typical application" a value to
compare KAVACH's recommendation against. It never substitutes for or
changes baseline_l_per_plant_day (the theoretical requirement) or
optimized_l_per_plant_day (KAVACH's recommendation) -- both keep their
existing, already-tested meaning unchanged.
"""


@dataclass(frozen=True)
class ConfigParameterResult:
    value: float | None
    note: str
    provenance: str = STATUS_PROJECT_DEFINED


def _find_row(db: Session, crop: str, parameter_name: str) -> AgronomicParameter | None:
    return (
        db.query(AgronomicParameter)
        .filter(
            AgronomicParameter.crop == crop,
            AgronomicParameter.parameter_name == parameter_name,
            AgronomicParameter.status == STATUS_PROJECT_DEFINED,
        )
        .first()
    )


def load_numeric_parameter(db: Session, crop: str, parameter_name: str) -> ConfigParameterResult:
    row = _find_row(db, crop, parameter_name)
    if row is None or row.value_numeric is None:
        return ConfigParameterResult(
            None,
            f"No project_defined '{parameter_name}' row found -- "
            "run `python -m app.services.optimization.seed_parameters` first.",
        )
    return ConfigParameterResult(row.value_numeric, PROJECT_DEFINED_DISCLAIMER)


def load_irrigation_baseline_for_stage(db: Session, crop: str, stage_name: str) -> ConfigParameterResult:
    parameter_name = BASELINE_IRRIGATION_PARAM_BY_STAGE_NAME.get(stage_name)
    if parameter_name is None:
        return ConfigParameterResult(
            None,
            f"No approved baseline_irrigation parameter exists for stage {stage_name!r} -- "
            "only kc_initial_stage/kc_mid_stage/kc_late_stage are approved.",
        )
    return load_numeric_parameter(db, crop, parameter_name)


def load_irrigation_adjustment_pct(db: Session, crop: str, severity: str) -> ConfigParameterResult:
    parameter_name = IRRIGATION_ADJUSTMENT_PARAM_BY_SEVERITY.get(severity)
    if parameter_name is None:
        return ConfigParameterResult(None, f"No irrigation adjustment defined for severity {severity!r}.")
    return load_numeric_parameter(db, crop, parameter_name)


def load_nutrient_adjustment_pct(db: Session, crop: str, severity: str) -> ConfigParameterResult:
    parameter_name = NUTRIENT_ADJUSTMENT_PARAM_BY_SEVERITY.get(severity)
    if parameter_name is None:
        return ConfigParameterResult(None, f"No nutrient adjustment defined for severity {severity!r}.")
    return load_numeric_parameter(db, crop, parameter_name)


def load_review_cycle_days(db: Session, crop: str) -> ConfigParameterResult:
    return load_numeric_parameter(db, crop, PARAM_REVIEW_CYCLE_DAYS)


def load_typical_application_multiplier_pct(db: Session, crop: str) -> ConfigParameterResult:
    return load_numeric_parameter(db, crop, PARAM_TYPICAL_APPLICATION_MULTIPLIER_PCT)


def load_irrigation_efficiency_pct(
    db: Session, crop: str, irrigation_system_type: str | None, farmer_override_pct: float | None
) -> tuple[float | None, str, str]:
    """
    Precedence (approved, exact order):
      1. explicit farmer irrigation_efficiency_pct override
      2. irrigation_system_type lookup
      3. unknown default

    Returns (efficiency_pct, source_label, note).
    """
    if farmer_override_pct is not None:
        return farmer_override_pct, "farmer_override", (
            f"Farmer-supplied irrigation_efficiency_pct override ({farmer_override_pct}%), "
            "not a project-defined value."
        )

    system_key = (irrigation_system_type or "").strip().lower()
    parameter_name = IRRIGATION_EFFICIENCY_PARAM_BY_SYSTEM_TYPE.get(system_key)
    if parameter_name is not None:
        result = load_numeric_parameter(db, crop, parameter_name)
        if result.value is not None:
            return result.value, "system_type_lookup", (
                f"{PROJECT_DEFINED_DISCLAIMER} (irrigation_system_type={system_key})"
            )

    result = load_numeric_parameter(db, crop, PARAM_IRRIGATION_EFFICIENCY_UNKNOWN_DEFAULT)
    return result.value, "unknown_default", (
        f"{PROJECT_DEFINED_DISCLAIMER} (irrigation_system_type unspecified or unrecognized -- "
        "using the unknown-system conservative default)"
    )
