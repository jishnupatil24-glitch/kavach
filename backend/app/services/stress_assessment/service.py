"""
Phase 4 orchestrator. `assess_run()` is the single entrypoint both the
automatic pipeline (via history.py's Workflow A) and the CLI/API
(Workflow B, read path) ultimately trace back to -- neither may
duplicate the evidence/gate logic in this module or its sibling
modules (enforced structurally by tests/test_stress_assessment.py).

Consumes ONLY: app.services.state_analysis.history.get_stored_analysis
(Phase 3's own read path -- never app.services.state_analysis.service
.analyze_run, which would mean Phase 4 recomputing Phase 3's trend/
rate/persistence/ICAR-deviation math itself), the raw
`sensor_observations` rows for the ONE analysis day (descriptive 6-hour
range only, never a new trend calculation), and `AgronomicParameter`
(Phase 1, read-only, `status="sourced"` rows only). Never imports any
app.services.simulator module, and never imports
app.services.state_analysis.trend/persistence/icar_deviation directly
-- those calculations belong to Phase 3 alone.

ALL 10 categories are always present in the result (including
insufficient_data/no_evidence ones) -- intentional, for auditability;
see docs/PROJECT_STATE.md's Phase 4 section for why. `problems()`
below is the filtered (weak_evidence+) view Phase 5 would consume.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.sensor_observation import SensorObservation
from app.services.state_analysis.crop_stage_context import StageMatch
from app.services.state_analysis.history import get_stored_analysis
from app.services.state_analysis.service import InvalidDayError, RunNotFoundError, StateAnalysisError
from app.services.stress_assessment.categories import CATEGORIES
from app.services.stress_assessment.evidence import (
    STATUS_CORROBORATED_EVIDENCE,
    STATUS_WEAK_EVIDENCE,
    ProblemAssessment,
    compute_problem_assessment,
    compute_raw_range,
)

# Re-exported so callers (CLI/routes) can catch Phase 4 failures without
# importing app.services.state_analysis.service directly -- the failure
# modes (unknown run, out-of-range day) are identical because Phase 4
# is strictly downstream of Phase 3's own validation.
__all__ = [
    "StateAnalysisError", "RunNotFoundError", "InvalidDayError",
    "StressAssessment", "assess_run",
]


@dataclass(frozen=True)
class StressAssessment:
    run_id: int
    crop: str
    assessment_day: int
    problems: list[ProblemAssessment]
    crop_stages: list[StageMatch]

    def evidenced_problems(self) -> list[ProblemAssessment]:
        """The filtered view: only categories that reached at least
        weak_evidence -- what Phase 5 would actually consume."""
        return [p for p in self.problems if p.status in (STATUS_WEAK_EVIDENCE, STATUS_CORROBORATED_EVIDENCE)]


def assess_run(db: Session, run_id: int, day: int | None = None) -> StressAssessment:
    analysis = get_stored_analysis(db, run_id, day=day)
    if analysis is None:
        raise InvalidDayError(
            f"No persisted Phase 3 state analysis found for simulation run {run_id}"
            + (f" at day {day}" if day is not None else "")
            + " -- Phase 4 cannot assess a run that has no Phase 3 history yet."
        )

    raw_observations = (
        db.query(SensorObservation)
        .filter(
            SensorObservation.simulation_run_id == run_id,
            SensorObservation.day == analysis.analysis_day,
        )
        .all()
    )

    by_field = {pa.current.field: pa for pa in analysis.parameters}

    problems: list[ProblemAssessment] = []
    for category in CATEGORIES:
        pa = by_field[category.field]
        raw_range = compute_raw_range(raw_observations, category.field)
        problems.append(
            compute_problem_assessment(db, analysis.crop, category, pa, raw_range, run_id=analysis.run_id)
        )

    return StressAssessment(
        run_id=analysis.run_id,
        crop=analysis.crop,
        assessment_day=analysis.analysis_day,
        problems=problems,
        crop_stages=analysis.crop_stages,
    )
