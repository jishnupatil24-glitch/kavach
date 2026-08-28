"""
WORKFLOW A -- backend persistence of Phase 5 decision-engine output for
an ENTIRE completed simulation run. Separate from, and never called by,
the Phase 5 CLI (Workflow B) -- see app/decision_cli.py's own docstring
for that boundary.

    Phase 4 problem_assessment_history (already persisted, one row/day)
        -> app.services.decision_engine.service.decide_run(db, run_id,
           day=day) per day -- reusing Phase 4's own read path, never
           recomputing evidence/severity/duration
        -> one decision_history row per day, 10 category decisions each

`persist_run_decisions()` is called automatically, once, at the end of
app.services.simulator.run_service.create_run() -- immediately after
Phase 4's own persist_run_assessments() call, so Phase 4's history for
every day of the run already exists before Phase 5 ever reads it. This
module's own `main()` below remains available as a manual/backfill
entrypoint.
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
from app.models.decision_history import DecisionHistory
from app.models.simulation_run import SimulationRun
from app.services.decision_engine.constraint_engine import GateCheck
from app.services.decision_engine.service import DecisionAssessment, RunNotFoundError, decide_run
from app.services.decision_engine.validation import DecisionRecord


def persist_run_decisions(db: Session, run_id: int) -> int:
    """
    Computes and stores one decision_history row per day of the run's
    full duration (day 1..duration_days), each via the existing
    decide_run(). Idempotent: deletes any existing rows for this
    run_id first, same delete-then-reinsert convention as Phase 3/4's
    own history modules.

    Returns the number of day-rows written.
    """
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    db.query(DecisionHistory).filter(DecisionHistory.simulation_run_id == run_id).delete()

    count = 0
    for day in range(1, run.duration_days + 1):
        assessment = decide_run(db, run_id, day=day)
        db.add(
            DecisionHistory(
                simulation_run_id=run_id,
                day=day,
                crop=assessment.crop,
                decisions_json=json.dumps([dataclasses.asdict(d) for d in assessment.decisions]),
            )
        )
        count += 1

    db.commit()
    return count


_LEGACY_DECISION_NOTE = (
    "LEGACY FORMAT: this row's stored shape does not match the current DecisionRecord "
    "fields -- re-run `python -m app.services.decision_engine.history --run-id <id>` "
    "to recompute it under the current definition."
)


def _decision_from_dict(d: dict) -> DecisionRecord:
    return DecisionRecord(
        category=d["category"],
        label=d["label"],
        status=d["status"],
        severity=d["severity"],
        abnormal_duration_days=d["abnormal_duration_days"],
        abnormal_duration_tier=d["abnormal_duration_tier"],
        eligibility_checks=[GateCheck(**c) for c in d["eligibility_checks"]],
        conflict_with=d["conflict_with"],
        outcome=d["outcome"],
        action_label=d["action_label"],
        action_type=d["action_type"],
        action_basis=d["action_basis"],
        decision_provenance=d["decision_provenance"],
        quantitative_basis=d["quantitative_basis"],
        limitations=d["limitations"],
        priority=d["priority"],
        priority_reason=d["priority_reason"],
    )


def get_stored_decision(db: Session, run_id: int, day: int | None = None) -> DecisionAssessment | None:
    """
    Reads a previously PERSISTED Phase 5 decision assessment (Workflow
    A's output) for one run -- never computes one. Returns None if
    nothing has been persisted yet for this run, or for the requested
    day specifically.
    """
    from app.services.stress_assessment.service import InvalidDayError

    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")
    if day is not None and not (1 <= day <= run.duration_days):
        raise InvalidDayError(
            f"day must be between 1 and {run.duration_days} for simulation run {run_id}"
        )

    query = db.query(DecisionHistory).filter(DecisionHistory.simulation_run_id == run_id)
    row = (
        query.filter(DecisionHistory.day == day).first()
        if day is not None
        else query.order_by(DecisionHistory.day.desc()).first()
    )
    if row is None:
        return None

    return DecisionAssessment(
        run_id=run_id,
        crop=row.crop,
        assessment_day=row.day,
        decisions=[_decision_from_dict(d) for d in json.loads(row.decisions_json)],
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.decision_engine.history",
        description=(
            "KAVACH Phase 5 backend processing (Workflow A): compute and "
            "persist daily decision-engine history for a completed simulation run."
        ),
    )
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            count = persist_run_decisions(db, args.run_id)
        except RunNotFoundError as e:
            print(f"✗ {e}")
            return 1
        print(f"✓ Persisted {count} daily decision record(s) for simulation run {args.run_id}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
