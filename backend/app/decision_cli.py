"""
WORKFLOW B -- presentation-only terminal front-end for Phase 5.
Contains ZERO eligibility/priority/validation logic of its own. It
reads and formats ALREADY-PERSISTED/ALREADY-STORED data via:
  - app.services.decision_engine.history.get_stored_decision
    (Phase 5's own persisted history -- never calls decide_run())
  - app.services.stress_assessment.history.get_stored_assessment
    (Phase 4's own persisted history, for the PHASE 4 INPUT section --
    never calls assess_run())

If nothing has been persisted yet for the requested run/day, this CLI
says so and stops -- it does not silently compute one on the fly. Use
`python -m app.services.decision_engine.history --run-id N` (Workflow
A, a separate backend step) to build/refresh that history first --
though under the automatic pipeline (run_service.create_run), this
should already exist for every run created through the normal path.

Usage:
    python -m app.decision_cli --run-id 12
    python -m app.decision_cli --run-id 12 --day 35
"""
from __future__ import annotations

import argparse
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from app.database.session import Base, SessionLocal, engine
from app.services.decision_engine.history import get_stored_decision
from app.services.decision_engine.service import DecisionAssessment, StateAnalysisError
from app.services.stress_assessment.history import get_stored_assessment

WIDTH = 78


def fail(message: str) -> None:
    print(f"✗ {message}")


def _fmt_gate(check) -> str:
    symbol = {True: "PASS", False: "FAIL", None: "N/A "}[check.passed]
    return f"    [{symbol}] {check.name}: {check.detail}"


def print_phase4_input(db, run_id: int, day: int) -> None:
    print("-" * WIDTH)
    print("PHASE 4 INPUT (stored, read-only)")
    print("-" * WIDTH)
    print()
    stress = get_stored_assessment(db, run_id, day=day)
    if stress is None:
        print("  (no persisted Phase 4 history found for this run/day)")
        return
    for p in stress.problems:
        if p.status in ("no_evidence", "insufficient_data"):
            continue
        print(f"{p.label}:")
        print(f"  Evidence status : {p.status}")
        print(f"  Severity        : {p.severity}")
        ad = p.abnormal_state_duration
        days_display = f"{ad.days} days" if ad.days is not None else "n/a"
        print(f"  Abnormal duration: {days_display} (tier: {ad.tier})")
        print()


def print_5a(assessment: DecisionAssessment) -> None:
    print("-" * WIDTH)
    print("5A -- CONSTRAINT ENGINE")
    print("-" * WIDTH)
    print()
    for d in assessment.decisions:
        if not d.eligibility_checks:
            continue
        print(f"{d.label} [{d.category}]:")
        for check in d.eligibility_checks:
            print(_fmt_gate(check))
        if d.conflict_with:
            print(f"    [CONFLICT] shares a sensor field with {d.conflict_with!r} -- both show live evidence")
        print()


def print_5b(assessment: DecisionAssessment) -> None:
    print("-" * WIDTH)
    print("5B -- ACTION PRIORITIZATION")
    print("-" * WIDTH)
    print()
    prioritized = sorted(
        (d for d in assessment.decisions if d.priority is not None),
        key=lambda d: d.priority,
    )
    if not prioritized:
        print("  No eligible actions to prioritize.")
    for d in prioritized:
        print(f"  #{d.priority}  {d.label} -- {d.priority_reason}")
    print()


def print_5c_and_final(assessment: DecisionAssessment) -> None:
    print("-" * WIDTH)
    print("5C -- RECOMMENDATION VALIDATION / FINAL DECISION")
    print("-" * WIDTH)
    print()
    print(f"{'Category':<22}{'Outcome':<20}{'Action'}")
    print("-" * WIDTH)
    for d in assessment.decisions:
        print(f"{d.label:<22}{d.outcome:<20}{d.action_label or '-'}")
    print()

    for d in assessment.decisions:
        if d.outcome not in ("ACTION_RECOMMENDED", "CONFLICT"):
            continue
        print(f"[{d.label}] outcome: {d.outcome}")
        print(f"    Evidence status: {d.status}   Severity: {d.severity}")
        print(f"    Recommended action: {d.action_label or 'n/a'}")
        print(f"    Action type: {d.action_type or 'n/a'}")
        print(f"    Action basis: {d.action_basis}")
        print(f"    Provenance: {d.decision_provenance}")
        print(f"    Quantitative basis: {d.quantitative_basis if d.quantitative_basis is not None else 'UNAVAILABLE -- not fabricated'}")
        for lim in d.limitations:
            print(f"    Limitation: {lim}")
        if d.conflict_with:
            print(f"    Conflicts with: {d.conflict_with}")
        print()


def print_decision_assessment(assessment: DecisionAssessment, db=None, run_id: int | None = None, show_header: bool = True) -> None:
    if show_header:
        print("=" * WIDTH)
        print("KAVACH -- PHASE 5 DECISION ENGINE".center(WIDTH))
        print("=" * WIDTH)
        print()
        print(f"Simulation ID  : {assessment.run_id}")
        print(f"Assessment Day : {assessment.assessment_day}")
        print(f"Crop           : {assessment.crop.capitalize()}")
        print()

    if db is not None and run_id is not None:
        print_phase4_input(db, run_id, assessment.assessment_day)
        print()

    print_5a(assessment)
    print_5b(assessment)
    print_5c_and_final(assessment)
    print("=" * WIDTH)


def fetch_and_print(db, run_id: int, day: int | None) -> int:
    try:
        assessment = get_stored_decision(db, run_id, day=day)
    except StateAnalysisError as e:
        fail(str(e))
        return 1

    if assessment is None:
        day_clause = f" at day {day}" if day is not None else ""
        fail(
            f"No persisted Phase 5 decision found for simulation run {run_id}{day_clause}. "
            f"Run `python -m app.services.decision_engine.history --run-id {run_id}` "
            "first to build the backend history."
        )
        return 1

    print_decision_assessment(assessment, db=db, run_id=run_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.decision_cli",
        description="KAVACH Phase 5 decision-engine CLI",
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--day", type=int, default=None)
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return fetch_and_print(db, args.run_id, args.day)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
