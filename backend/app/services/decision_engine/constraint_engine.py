"""
5A -- Constraint Engine: "what actions are valid/permissible?"

Consumes ONLY Phase 4's already-computed ProblemAssessment (status,
severity, abnormal_state_duration) plus the two approved project_defined
configuration parameters (config_parameters.py). Never re-reads raw
sensor data, never recomputes trend/persistence/ICAR-deviation/severity
-- those stay Phase 3/4's alone.

Two responsibilities, matching the approved design exactly:
  1. evaluate_eligibility() -- per-category gate (severity floor, and
     for Tier-2 categories, abnormal-duration floor).
  2. detect_conflicts() -- cross-category: do two categories sharing a
     sensor field both show live evidence in opposite directions at
     once. A structural fact derivable from the category taxonomy
     itself (which field each category watches), not agronomic
     knowledge -- never resolved silently (see validation.py).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.services.decision_engine.config_parameters import SEVERITY_ORDER
from app.services.stress_assessment.abnormal_duration import TIER_ICAR_SIGN_TREND_PROXY
from app.services.stress_assessment.evidence import ProblemAssessment

STATUS_CANDIDATE_VALUES = ("weak_evidence", "corroborated_evidence")

CONFLICT_PAIRS = (
    ("water_depletion", "excessive_moisture"),   # both watch soil_moisture_pct
    ("humidity_low", "humidity_high"),           # both watch humidity_pct
    ("heat_related", "temperature_deficit"),     # both watch temperature_c
)
"""
Structural fact from app.services.stress_assessment.categories's own
field-sharing (each pair watches the same sensor field in opposite
adverse directions) -- design-time enumerable, not a database lookup,
not agronomic knowledge. Kept as a plain tuple here rather than
importing categories.py, to avoid coupling this module to Phase 4's
internal ProblemCategory objects for a fact that is already fixed.
"""


@dataclass(frozen=True)
class GateCheck:
    name: str
    passed: bool | None  # True=passed, False=evaluated and failed, None=not evaluable (missing data/config)
    detail: str


@dataclass(frozen=True)
class EligibilityResult:
    category: str
    tier: str
    gate_checks: list[GateCheck] = field(default_factory=list)
    eligible: bool = False


def evaluate_eligibility(
    problem: ProblemAssessment,
    min_severity: str | None,
    min_severity_note: str,
    tier2_min_days: int | None,
    tier2_min_days_note: str,
) -> EligibilityResult:
    tier = problem.abnormal_state_duration.tier
    checks: list[GateCheck] = []

    status_ok = problem.status in STATUS_CANDIDATE_VALUES
    checks.append(GateCheck("evidence_status", status_ok, f"status={problem.status}"))
    if not status_ok:
        return EligibilityResult(problem.category, tier, checks, eligible=False)

    if problem.severity == "insufficient_data":
        checks.append(GateCheck("severity_floor", None, "severity is insufficient_data -- gate not evaluable"))
        return EligibilityResult(problem.category, tier, checks, eligible=False)

    if min_severity is None:
        checks.append(GateCheck("severity_floor", None, min_severity_note))
        return EligibilityResult(problem.category, tier, checks, eligible=False)

    severity_ok = SEVERITY_ORDER[problem.severity] >= SEVERITY_ORDER[min_severity]
    checks.append(
        GateCheck(
            "severity_floor", severity_ok,
            f"severity={problem.severity} vs configured floor={min_severity}",
        )
    )

    if tier == TIER_ICAR_SIGN_TREND_PROXY:
        if problem.abnormal_state_duration.days is None:
            checks.append(GateCheck("duration_floor", None, "abnormal_state_duration.days is missing -- gate not evaluable"))
        elif tier2_min_days is None:
            checks.append(GateCheck("duration_floor", None, tier2_min_days_note))
        else:
            duration_ok = problem.abnormal_state_duration.days >= tier2_min_days
            checks.append(
                GateCheck(
                    "duration_floor", duration_ok,
                    f"abnormal_state_duration.days={problem.abnormal_state_duration.days} vs configured floor={tier2_min_days}",
                )
            )

    eligible = all(c.passed is True for c in checks)
    return EligibilityResult(problem.category, tier, checks, eligible=eligible)


def detect_conflicts(problems_by_category: dict[str, ProblemAssessment]) -> dict[str, str | None]:
    """
    Returns {category: conflicting_category_or_None}. A conflict is
    "both sides of a shared-field pair currently show at least
    weak_evidence" -- an evidence-level fact, independent of whether
    either side separately passes the eligibility gates above. Never
    silently resolved: both categories in a detected pair are flagged.
    """
    conflict_with: dict[str, str | None] = {cat: None for cat in problems_by_category}
    for a, b in CONFLICT_PAIRS:
        pa, pb = problems_by_category.get(a), problems_by_category.get(b)
        if pa is None or pb is None:
            continue
        if pa.status in STATUS_CANDIDATE_VALUES and pb.status in STATUS_CANDIDATE_VALUES:
            conflict_with[a] = b
            conflict_with[b] = a
    return conflict_with
