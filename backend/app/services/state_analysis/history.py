"""
WORKFLOW A -- backend persistence of Phase 3 state history for an
ENTIRE completed Phase 2 simulation run. Separate from, and never
called by, the Phase 3 CLI (Workflow B) -- see
app/state_analysis_cli.py's own docstring for that boundary.

    sensor_observations (Phase 2, 4 readings/day)
        -> grouped by day (one call to
           app.services.state_analysis.service.analyze_run(db, run_id,
           day=day) per day -- reusing the EXACT SAME trend/rate/
           persistence/ICAR calculation as the on-demand path, never a
           second implementation)
        -> one state_analysis_history row per day

A 60-day run therefore produces exactly 60 rows here, one per day,
matching its 240 raw sensor_observations rows (60 days x 4 slots/day).

`persist_run_history()` is called automatically, once, at the end of
app.services.simulator.run_service.create_run() -- the single common
path both the simulator API (POST /api/simulator/runs) and the
simulator CLI (python -m app.simulator_cli) already funnel every
successful run through, so no other Phase 2 call site needed to be
touched. It runs only after that run's sensor_observations are already
committed. This module's own `main()` below
(`python -m app.services.state_analysis.history --run-id N`) remains
available as a manual/backfill entrypoint -- e.g. to (re)build history
for a run created before this automatic wiring existed -- but is no
longer the normal way this table gets populated.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys

# Windows terminals commonly default to a legacy codepage that cannot
# encode the checkmark/cross characters printed by main() below -- same
# fix as app/simulator_cli.py and app/state_analysis_cli.py.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from sqlalchemy.orm import Session

from app.database.session import Base, SessionLocal, engine
from app.models.simulation_run import SimulationRun
from app.models.state_analysis_history import StateAnalysisHistory
from app.services.state_analysis.crop_stage_context import AgronomicContextItem, StageMatch
from app.services.state_analysis.current_state import CurrentState
from app.services.state_analysis.icar_deviation import IcarDeviation
from app.services.state_analysis.persistence import PersistenceResult
from app.services.state_analysis.service import (
    InvalidDayError,
    ParameterAnalysis,
    RunNotFoundError,
    StateAnalysis,
    analyze_run,
)
from app.services.state_analysis.trend import TrendResult


def persist_run_history(db: Session, run_id: int) -> int:
    """
    Computes and stores one state_analysis_history row per day of the
    run's full duration (day 1..duration_days), each via the existing
    analyze_run(). Idempotent: deletes any existing rows for this
    run_id first, so re-running never leaves stale or duplicate rows
    (mirrors app.services.seed_agronomics.seed()'s own
    delete-then-reinsert convention).

    Returns the number of day-rows written.
    """
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run_id).delete()

    count = 0
    for day in range(1, run.duration_days + 1):
        analysis = analyze_run(db, run_id, day=day)
        db.add(
            StateAnalysisHistory(
                simulation_run_id=run_id,
                day=day,
                crop=analysis.crop,
                parameters_json=json.dumps([dataclasses.asdict(pa) for pa in analysis.parameters]),
                crop_stages_json=json.dumps([dataclasses.asdict(s) for s in analysis.crop_stages]),
                agronomic_context_json=json.dumps(
                    [dataclasses.asdict(i) for i in analysis.agronomic_context]
                ),
                data_quality_notes_json=json.dumps(analysis.data_quality_notes),
            )
        )
        count += 1

    db.commit()
    return count


_LEGACY_FORMAT_NOTE = (
    "LEGACY FORMAT: this run's Phase 3 history was persisted before the "
    "daily-aggregation change -- this value is the single latest 6-hour "
    "reading, NOT a recomputed daily average. Run `python -m "
    "app.services.state_analysis.history --run-id <id>` to recompute it "
    "under the current daily-aggregation definition."
)


def _parameter_analysis_from_dict(d: dict) -> ParameterAnalysis:
    current_dict = d["current"]
    if "n_readings" in current_dict:
        current = CurrentState(**current_dict)
    else:
        # Row was persisted before the daily-aggregation change (its
        # `current` shape had `hour`, not `n_readings`/`note`). Read it
        # rather than crash, but say plainly that this value predates
        # the current calculation -- never silently presented as an
        # up-to-date daily average.
        current = CurrentState(
            parameter=current_dict["parameter"],
            field=current_dict["field"],
            value=current_dict["value"],
            day=current_dict["day"],
            n_readings=1,
            note=_LEGACY_FORMAT_NOTE,
        )
    return ParameterAnalysis(
        current=current,
        trend=TrendResult(**d["trend"]),
        persistence=PersistenceResult(**d["persistence"]),
        icar=IcarDeviation(**d["icar"]),
    )


def get_stored_analysis(db: Session, run_id: int, day: int | None = None) -> StateAnalysis | None:
    """
    Reads a previously PERSISTED Phase 3 analysis (Workflow A's output)
    for one run -- never computes one. Returns None if nothing has
    been persisted yet for this run, or for the requested day
    specifically, so the caller (the Phase 3 CLI) can say so honestly
    rather than silently falling back to on-demand calculation.
    """
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")
    if day is not None and not (1 <= day <= run.duration_days):
        raise InvalidDayError(
            f"day must be between 1 and {run.duration_days} for simulation run {run_id}"
        )

    query = db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run_id)
    row = (
        query.filter(StateAnalysisHistory.day == day).first()
        if day is not None
        else query.order_by(StateAnalysisHistory.day.desc()).first()
    )
    if row is None:
        return None

    return StateAnalysis(
        run_id=run_id,
        crop=row.crop,
        analysis_day=row.day,
        duration_days=run.duration_days,
        parameters=[_parameter_analysis_from_dict(d) for d in json.loads(row.parameters_json)],
        crop_stages=[StageMatch(**d) for d in json.loads(row.crop_stages_json)],
        agronomic_context=[AgronomicContextItem(**d) for d in json.loads(row.agronomic_context_json)],
        data_quality_notes=json.loads(row.data_quality_notes_json),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.state_analysis.history",
        description=(
            "KAVACH Phase 3 backend processing (Workflow A): compute and "
            "persist daily state-analysis history for a completed Phase 2 "
            "simulation run."
        ),
    )
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            count = persist_run_history(db, args.run_id)
        except RunNotFoundError as e:
            print(f"✗ {e}")
            return 1
        print(f"✓ Persisted {count} daily state-analysis record(s) for simulation run {args.run_id}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
