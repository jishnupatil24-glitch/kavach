"""
5C -- Recommendation Validation: "is the selected recommendation
actually justified, supported, feasible, and explainable?" Fully
deterministic -- no LLM anywhere in this module or its callers.

Combines Phase 4's own status, 5A's eligibility gate result and
conflict flag, and Phase 5's action-label vocabulary into one
DecisionRecord per category, using the exact fixed outcome vocabulary
and precedence approved in design:

  no_evidence status                          -> NO_ACTION
  insufficient_data status                     -> INSUFFICIENT_SUPPORT
  cross-category conflict flagged              -> CONFLICT
  any eligibility gate not evaluable (None)     -> INSUFFICIENT_SUPPORT
  eligibility gate evaluated and failed         -> MONITOR
  eligible but no action label defined          -> INSUFFICIENT_SUPPORT
  eligible and action label defined             -> ACTION_RECOMMENDED

ACTION_RECOMMENDED means KAVACH's deterministic rules permit a
recommendation -- it is NEVER itself an externally proven agronomic
diagnosis, an ICAR-confirmed intervention, or scientific certainty.
Phase 4's own evidence status/severity/duration are echoed on the
record UNCHANGED and stay visibly independent of this outcome.

QUANTITATIVE ACTIONS ARE NEVER PRODUCED: no numeric intervention
parameter (irrigation mm, fertilizer kg, frequency, cost, etc.) exists
anywhere in this project's knowledge base (confirmed by repository
audit) -- action_type is always "QUALITATIVE" when an action is
recommended, quantitative_basis is always None, and a limitation
stating this is always attached.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.agronomic_parameter import AgronomicParameter
from app.services.decision_engine.actions import get_action_label
from app.services.decision_engine.constraint_engine import EligibilityResult, GateCheck
from app.services.stress_assessment.abnormal_duration import TIER_SOURCED_THRESHOLD
from app.services.stress_assessment.evidence import ProblemAssessment

OUTCOME_ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
OUTCOME_MONITOR = "MONITOR"
OUTCOME_NO_ACTION = "NO_ACTION"
OUTCOME_INSUFFICIENT_SUPPORT = "INSUFFICIENT_SUPPORT"
OUTCOME_CONFLICT = "CONFLICT"

ACTION_TYPE_QUALITATIVE = "QUALITATIVE"

QUANTITATIVE_UNAVAILABLE_LIMITATION = (
    "No quantitative agronomic/operational parameter (irrigation quantity, fertilizer "
    "quantity, frequency, cost, or similar) exists in the current knowledge base for "
    "this category -- recommendation is qualitative only, never a fabricated quantity."
)

_PARTIAL_CITATION_PARAMETER = {
    "temperature_deficit": "temperature_min_c",
    "nitrogen_related": "n_total_requirement_g_plant_season",
    "phosphorus_related": "p2o5_total_requirement_g_plant_season",
    "potassium_related": "k2o_total_requirement_g_plant_season",
    "light_deficit": "dli_target_mol_m2_day",
}
"""
Categories with a sourced-but-not-actionable agronomic_parameters row
(day/stage-unmapped, or an unconvertible kg/ha season total) -- surfaced
in the decision record as citation/limitation text only, per the
approved rule: never used as a quantitative action gate.
"""


@dataclass(frozen=True)
class DecisionRecord:
    category: str
    label: str
    status: str  # Phase 4's own status, echoed unchanged
    severity: str  # Phase 4's own severity, echoed unchanged
    abnormal_duration_days: int | None  # Phase 4's own, echoed unchanged
    abnormal_duration_tier: str
    eligibility_checks: list[GateCheck]
    conflict_with: str | None
    outcome: str
    action_label: str | None
    action_type: str | None  # "QUALITATIVE" or None
    action_basis: str  # reused Phase 4 provenance_note text -- never re-derived
    decision_provenance: str  # "PROJECT_DEFINED" -- Phase 5's own gate is always this
    quantitative_basis: None  # always None -- see module docstring
    limitations: list[str] = field(default_factory=list)
    priority: int | None = None
    priority_reason: str | None = None


def _partial_citation_limitation(db: Session, crop: str, category: str) -> str | None:
    parameter_name = _PARTIAL_CITATION_PARAMETER.get(category)
    if parameter_name is None:
        return None
    row = (
        db.query(AgronomicParameter)
        .filter(
            AgronomicParameter.crop == crop,
            AgronomicParameter.parameter_name == parameter_name,
            AgronomicParameter.status == "sourced",
        )
        .first()
    )
    if row is None:
        return None
    value = row.value_text or (
        f"{row.value_min}-{row.value_max}{row.unit or ''}"
        if row.value_min is not None
        else f"{row.value_numeric}{row.unit or ''}"
    )
    return (
        f"A sourced value exists for {parameter_name} ({value}), but it is not usable as a "
        "quantitative action gate here (day/stage not applicable to this run, or unconvertible "
        "without additional configuration not yet present) -- shown for provenance only."
    )


def build_decision_record(
    db: Session,
    crop: str,
    problem: ProblemAssessment,
    eligibility: EligibilityResult,
    conflict_with: str | None,
) -> DecisionRecord:
    limitations: list[str] = []
    action_label: str | None = None
    action_type: str | None = None
    quantitative_basis = None

    if problem.status == "no_evidence":
        outcome = OUTCOME_NO_ACTION
    elif problem.status == "insufficient_data":
        outcome = OUTCOME_INSUFFICIENT_SUPPORT
    elif conflict_with is not None:
        outcome = OUTCOME_CONFLICT
        limitations.append(
            f"Category '{problem.category}' and '{conflict_with}' both show live evidence on the "
            "same sensor field in opposite directions on the same day -- not silently resolved."
        )
    elif any(c.passed is None for c in eligibility.gate_checks):
        outcome = OUTCOME_INSUFFICIENT_SUPPORT
        limitations.extend(c.detail for c in eligibility.gate_checks if c.passed is None)
    elif not eligibility.eligible:
        outcome = OUTCOME_MONITOR
    else:
        action_label = get_action_label(problem.category)
        if action_label is None:
            outcome = OUTCOME_INSUFFICIENT_SUPPORT
            limitations.append(f"No Phase 5 action label defined for category {problem.category!r}.")
        else:
            outcome = OUTCOME_ACTION_RECOMMENDED
            action_type = ACTION_TYPE_QUALITATIVE
            limitations.append(QUANTITATIVE_UNAVAILABLE_LIMITATION)

    partial_note = _partial_citation_limitation(db, crop, problem.category)
    if partial_note is not None:
        limitations.append(partial_note)

    return DecisionRecord(
        category=problem.category,
        label=problem.label,
        status=problem.status,
        severity=problem.severity,
        abnormal_duration_days=problem.abnormal_state_duration.days,
        abnormal_duration_tier=problem.abnormal_state_duration.tier,
        eligibility_checks=eligibility.gate_checks,
        conflict_with=conflict_with,
        outcome=outcome,
        action_label=action_label,
        action_type=action_type,
        action_basis=problem.abnormal_state_duration.provenance_note,
        decision_provenance="PROJECT_DEFINED",
        quantitative_basis=quantitative_basis,
        limitations=limitations,
    )
