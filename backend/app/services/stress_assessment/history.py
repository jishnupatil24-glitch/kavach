"""
WORKFLOW A -- backend persistence of Phase 4 problem/stress assessment
history for an ENTIRE completed simulation run. Separate from, and
never called by, the Phase 4 CLI (Workflow B) -- see
app/stress_assessment_cli.py's own docstring for that boundary.

    Phase 3 state_analysis_history (already persisted, one row/day)
        -> app.services.stress_assessment.service.assess_run(db,
           run_id, day=day) per day -- reusing Phase 3's own read path,
           never recomputing trend/rate/persistence/ICAR-deviation
        -> one problem_assessment_history row per day, 10 category
           assessments each

`persist_run_assessments()` is called automatically, once, at the end
of app.services.simulator.run_service.create_run() -- immediately
after Phase 3's own persist_run_history() call, so Phase 3's history
for every day of the run already exists before Phase 4 ever reads it.
This module's own `main()` below
(`python -m app.services.stress_assessment.history --run-id N`)
remains available as a manual/backfill entrypoint.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from sqlalchemy.orm import Session

from app.database.session import Base, SessionLocal, engine
from app.models.problem_assessment_history import ProblemAssessmentHistory
from app.models.simulation_run import SimulationRun
from app.services.state_analysis.crop_stage_context import StageMatch
from app.services.stress_assessment.abnormal_duration import AbnormalDurationResult, classify_tier
from app.services.stress_assessment.evidence import (
    SEVERITY_INSUFFICIENT_DATA,
    ProblemAssessment,
    RawRangeNote,
    SeverityFactors,
)
from app.services.stress_assessment.service import RunNotFoundError, StressAssessment, assess_run


def persist_run_assessments(db: Session, run_id: int) -> int:
    """
    Computes and stores one problem_assessment_history row per day of
    the run's full duration (day 1..duration_days), each via the
    existing assess_run(). Idempotent: deletes any existing rows for
    this run_id first (same convention as Phase 3's
    persist_run_history and Phase 1's seed_agronomics.seed()).

    Returns the number of day-rows written.
    """
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    db.query(ProblemAssessmentHistory).filter(
        ProblemAssessmentHistory.simulation_run_id == run_id
    ).delete()

    count = 0
    for day in range(1, run.duration_days + 1):
        assessment = assess_run(db, run_id, day=day)
        db.add(
            ProblemAssessmentHistory(
                simulation_run_id=run_id,
                day=day,
                crop=assessment.crop,
                problems_json=json.dumps([dataclasses.asdict(p) for p in assessment.problems]),
            )
        )
        count += 1

    db.commit()
    return count


_LEGACY_SEVERITY_NOTE = (
    "LEGACY FORMAT: this run's Phase 4 history was persisted before the "
    "severity feature existed -- severity was never computed for this row. "
    "Run `python -m app.services.stress_assessment.history --run-id <id>` "
    "to recompute it."
)

_LEGACY_ABNORMAL_DURATION_NOTE = (
    "LEGACY FORMAT: this run's Phase 4 history was persisted before the "
    "abnormal_state_duration feature existed -- it was never computed for "
    "this row. Run `python -m app.services.stress_assessment.history "
    "--run-id <id>` to recompute it."
)


def _problem_from_dict(d: dict) -> ProblemAssessment:
    raw_range = d["raw_range"]
    if "severity" in d:
        severity = d["severity"]
        factors = d["severity_factors"]
        severity_factors = SeverityFactors(**factors) if factors is not None else None
        severity_disclaimer = d["severity_disclaimer"]
    else:
        # Row was persisted before the severity feature existed. Read it
        # rather than crash, but say plainly severity was never
        # computed for it -- never silently presented as LOW/insufficient.
        severity = SEVERITY_INSUFFICIENT_DATA
        severity_factors = None
        severity_disclaimer = _LEGACY_SEVERITY_NOTE

    if "abnormal_state_duration" in d and d["abnormal_state_duration"] is not None:
        abnormal_state_duration = AbnormalDurationResult(**d["abnormal_state_duration"])
    else:
        # Row was persisted before abnormal_state_duration existed. Read it
        # rather than crash, but say plainly it was never computed for this
        # row -- never silently presented as a real day count.
        abnormal_state_duration = AbnormalDurationResult(
            category=d["category"],
            tier=classify_tier(d["category"]),
            days=None,
            provenance_note=_LEGACY_ABNORMAL_DURATION_NOTE,
        )

    return ProblemAssessment(
        category=d["category"],
        label=d["label"],
        field=d["field"],
        status=d["status"],
        direction=d["direction"],
        current_value=d["current_value"],
        icar_value=d["icar_value"],
        icar_deviation=d["icar_deviation"],
        rate_per_day=d["rate_per_day"],
        rate_unit=d["rate_unit"],
        persistence_days=d["persistence_days"],
        sourced_corroboration_notes=d["sourced_corroboration_notes"],
        provenance_notes=d["provenance_notes"],
        raw_range=RawRangeNote(**raw_range) if raw_range is not None else None,
        severity=severity,
        severity_factors=severity_factors,
        severity_disclaimer=severity_disclaimer,
        abnormal_state_duration=abnormal_state_duration,
    )


def get_stored_assessment(db: Session, run_id: int, day: int | None = None) -> StressAssessment | None:
    """
    Reads a previously PERSISTED Phase 4 assessment (Workflow A's
    output) for one run -- never computes one. Returns None if nothing
    has been persisted yet for this run, or for the requested day
    specifically, so the caller (the Phase 4 CLI) can say so honestly
    rather than silently falling back to on-demand calculation.

    Reuses Phase 3's own get_stored_analysis for crop_stages context
    (already-resolved, day-mapped stages) rather than re-deriving it.
    """
    from app.services.state_analysis.history import get_stored_analysis

    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    query = db.query(ProblemAssessmentHistory).filter(
        ProblemAssessmentHistory.simulation_run_id == run_id
    )
    row = (
        query.filter(ProblemAssessmentHistory.day == day).first()
        if day is not None
        else query.order_by(ProblemAssessmentHistory.day.desc()).first()
    )
    if row is None:
        return None

    phase3 = get_stored_analysis(db, run_id, day=row.day)
    crop_stages: list[StageMatch] = phase3.crop_stages if phase3 is not None else []

    return StressAssessment(
        run_id=run_id,
        crop=row.crop,
        assessment_day=row.day,
        problems=[_problem_from_dict(d) for d in json.loads(row.problems_json)],
        crop_stages=crop_stages,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.stress_assessment.history",
        description=(
            "KAVACH Phase 4 backend processing (Workflow A): compute and "
            "persist daily problem/stress assessment history for a "
            "completed simulation run."
        ),
    )
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            count = persist_run_assessments(db, args.run_id)
        except RunNotFoundError as e:
            print(f"✗ {e}")
            return 1
        print(f"✓ Persisted {count} daily problem-assessment record(s) for simulation run {args.run_id}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
