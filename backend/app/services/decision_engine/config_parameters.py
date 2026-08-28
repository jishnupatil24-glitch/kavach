"""
Reads Phase 5's two approved project-defined decision-engine
configuration parameters from the EXISTING agronomic_parameters table
(status="project_defined") -- no new table, reusing the same
query shape app.services.stress_assessment.evidence's own sourced-
threshold lookups already use (crop + parameter_name + status filter).

Both parameters are KAVACH decision-engine configuration, never an
agronomic fact -- see app.models.agronomic_status's own
"project_defined" docstring entry.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.agronomic_parameter import AgronomicParameter

DOMAIN_OPERATIONAL = "operational"
STATUS_PROJECT_DEFINED = "project_defined"

PARAM_MIN_SEVERITY_FOR_ACTION = "min_severity_for_action"
PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS = "tier2_min_abnormal_duration_days_for_action"

PROJECT_DEFINED_DISCLAIMER = (
    "KAVACH project-defined prototype rule -- not an externally sourced agronomic fact."
)

SEVERITY_ORDER = {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
"""
Explicit integer ordinal -- eligibility comparisons use this mapping,
never a string comparison. Matches Phase 4's own
app.services.stress_assessment.evidence severity vocabulary exactly
(reused, not reinvented). "insufficient_data" is deliberately absent --
it is a separate sentinel (see config_parameters.load_min_severity's
caller in constraint_engine.py), never coerced to a number.
"""


@dataclass(frozen=True)
class ConfigParameterResult:
    value: str | int | None
    note: str


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


def load_min_severity_for_action(db: Session, crop: str) -> ConfigParameterResult:
    row = _find_row(db, crop, PARAM_MIN_SEVERITY_FOR_ACTION)
    if row is None or row.value_text is None:
        return ConfigParameterResult(
            None,
            f"No project_defined '{PARAM_MIN_SEVERITY_FOR_ACTION}' row found -- "
            "severity-floor gate cannot be evaluated.",
        )
    if row.value_text not in SEVERITY_ORDER:
        return ConfigParameterResult(
            None,
            f"project_defined '{PARAM_MIN_SEVERITY_FOR_ACTION}' value "
            f"{row.value_text!r} is not one of {sorted(SEVERITY_ORDER)} -- "
            "severity-floor gate cannot be evaluated.",
        )
    return ConfigParameterResult(row.value_text, f"{PROJECT_DEFINED_DISCLAIMER} (severity floor: {row.value_text})")


def load_tier2_min_abnormal_duration_days(db: Session, crop: str) -> ConfigParameterResult:
    row = _find_row(db, crop, PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS)
    if row is None or row.value_numeric is None:
        return ConfigParameterResult(
            None,
            f"No project_defined '{PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS}' row found -- "
            "Tier-2 duration-floor gate cannot be evaluated.",
        )
    return ConfigParameterResult(
        int(row.value_numeric),
        f"{PROJECT_DEFINED_DISCLAIMER} (duration floor: {int(row.value_numeric)} days)",
    )
