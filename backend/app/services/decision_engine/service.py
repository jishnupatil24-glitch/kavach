"""
Phase 5 orchestrator. `decide_run()` is the single entrypoint both the
CLI and the API call -- neither may duplicate the eligibility/priority/
validation logic in this module or its sibling modules (enforced
structurally by tests/test_decision_engine.py, mirroring Phase 3/4's
own convention).

Consumes ONLY: app.services.stress_assessment.history.get_stored_assessment
(Phase 4's OWN STORED history -- never app.services.stress_assessment
.service.assess_run, which would mean Phase 5 depending on Phase 4
recomputing anything). Never imports state_analysis.trend/persistence/
icar_deviation, never queries sensor_observations or
state_analysis_history directly. This is the hard boundary requested:
Phase 5 must not re-read raw sensor data or redo Phase 3/4 calculations.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from sqlalchemy.orm import Session

from app.services.decision_engine.config_parameters import (
    load_min_severity_for_action,
    load_tier2_min_abnormal_duration_days,
)
from app.services.decision_engine.constraint_engine import detect_conflicts, evaluate_eligibility
from app.services.decision_engine.prioritization import PriorityAssignment, prioritize
from app.services.decision_engine.validation import (
    OUTCOME_ACTION_RECOMMENDED,
    DecisionRecord,
    build_decision_record,
)
from app.services.stress_assessment.history import get_stored_assessment
from app.services.stress_assessment.service import InvalidDayError, RunNotFoundError, StateAnalysisError

__all__ = [
    "StateAnalysisError", "RunNotFoundError", "InvalidDayError",
    "DecisionAssessment", "decide_run",
]


@dataclass(frozen=True)
class DecisionAssessment:
    run_id: int
    crop: str
    assessment_day: int
    decisions: list[DecisionRecord]

    def recommended(self) -> list[DecisionRecord]:
        return [d for d in self.decisions if d.outcome == OUTCOME_ACTION_RECOMMENDED]


def decide_run(db: Session, run_id: int, day: int | None = None) -> DecisionAssessment:
    assessment = get_stored_assessment(db, run_id, day=day)
    if assessment is None:
        raise InvalidDayError(
            f"No persisted Phase 4 assessment found for simulation run {run_id}"
            + (f" at day {day}" if day is not None else "")
            + " -- Phase 5 cannot decide on a run that has no Phase 4 history yet."
        )

    problems_by_category = {p.category: p for p in assessment.problems}

    min_severity_result = load_min_severity_for_action(db, assessment.crop)
    min_severity, min_severity_note = min_severity_result.value, min_severity_result.note

    tier2_min_days_result = load_tier2_min_abnormal_duration_days(db, assessment.crop)
    tier2_min_days, tier2_min_days_note = tier2_min_days_result.value, tier2_min_days_result.note

    eligibility_by_category = {
        category: evaluate_eligibility(
            problem, min_severity, min_severity_note, tier2_min_days, tier2_min_days_note
        )
        for category, problem in problems_by_category.items()
    }
    conflict_by_category = detect_conflicts(problems_by_category)

    decisions: list[DecisionRecord] = [
        build_decision_record(
            db, assessment.crop, problem,
            eligibility_by_category[category], conflict_by_category[category],
        )
        for category, problem in problems_by_category.items()
    ]

    eligible_problems = [
        problems_by_category[d.category] for d in decisions
        if d.outcome == OUTCOME_ACTION_RECOMMENDED
    ]
    priority_by_category = prioritize(eligible_problems)
    decisions = [
        _with_priority(d, priority_by_category[d.category]) if d.category in priority_by_category else d
        for d in decisions
    ]

    return DecisionAssessment(
        run_id=assessment.run_id,
        crop=assessment.crop,
        assessment_day=assessment.assessment_day,
        decisions=decisions,
    )


def _with_priority(record: DecisionRecord, assignment: PriorityAssignment) -> DecisionRecord:
    return replace(record, priority=assignment.priority, priority_reason=assignment.reason)
