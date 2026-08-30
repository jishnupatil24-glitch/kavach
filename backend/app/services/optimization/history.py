"""
WORKFLOW A -- backend persistence of Phase 6 optimization output for an
ENTIRE completed simulation run. Separate from, and never called by,
the Phase 6 CLI (Workflow B) -- see app/optimization_cli.py's own
docstring for that boundary.

    Phase 5 decision_history (already persisted, one row/day)
        -> app.services.optimization.service.optimize_run(db, run_id,
           day=day) per day -- reusing Phase 5's own read path, never
           recomputing eligibility/priority/validation
        -> one optimization_history row per day

`persist_run_optimizations()` is called automatically, once, right
after a new simulation run's own Phase 5 decision history is written
-- immediately after Phase 5's own persist_run_decisions() call. This
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
from app.models.optimization_history import OptimizationHistory
from app.models.simulation_run import SimulationRun
from app.services.optimization.cost import CostResult
from app.services.optimization.feasibility import FeasibilityCheck
from app.services.optimization.nutrient_model import NutrientOptimization
from app.services.optimization.population import PlantPopulationResult
from app.services.optimization.service import (
    FarmConfigSnapshot,
    OptimizationAssessment,
    RunNotFoundError,
    UnsupportedCategoryNote,
    optimize_run,
)
from app.services.optimization.water_model import WaterOptimization


def persist_run_optimizations(db: Session, run_id: int) -> int:
    """
    Computes and stores one optimization_history row per day of the
    run's full duration. Idempotent: deletes any existing rows for
    this run_id first, same delete-then-reinsert convention as
    Phase 3/4/5's own history modules. Returns the number of day-rows
    written.
    """
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    db.query(OptimizationHistory).filter(OptimizationHistory.simulation_run_id == run_id).delete()

    count = 0
    for day in range(1, run.duration_days + 1):
        assessment = optimize_run(db, run_id, day=day)
        db.add(
            OptimizationHistory(
                simulation_run_id=run_id,
                day=day,
                crop=assessment.crop,
                optimization_json=json.dumps(dataclasses.asdict(assessment)),
            )
        )
        count += 1

    db.commit()
    return count


def _water_from_dict(d: dict) -> WaterOptimization:
    return WaterOptimization(
        **{**d, "plant_population": PlantPopulationResult(**d["plant_population"]),
           "feasibility": [FeasibilityCheck(**f) for f in d["feasibility"]],
           "cost": CostResult(**d["cost"])}
    )


def _nutrient_from_dict(d: dict) -> NutrientOptimization:
    return NutrientOptimization(
        **{**d, "plant_population": PlantPopulationResult(**d["plant_population"]),
           "cost": CostResult(**d["cost"])}
    )


def _optimization_from_dict(d: dict) -> OptimizationAssessment:
    return OptimizationAssessment(
        run_id=d["run_id"],
        crop=d["crop"],
        assessment_day=d["assessment_day"],
        farm_configuration=FarmConfigSnapshot(**d["farm_configuration"]),
        water_optimizations=[_water_from_dict(w) for w in d["water_optimizations"]],
        nutrient_optimizations=[_nutrient_from_dict(n) for n in d["nutrient_optimizations"]],
        unsupported=[UnsupportedCategoryNote(**u) for u in d["unsupported"]],
        multi_action_note=d["multi_action_note"],
        limitations=d["limitations"],
    )


def get_stored_optimization(db: Session, run_id: int, day: int | None = None) -> OptimizationAssessment | None:
    """
    Reads a previously PERSISTED Phase 6 optimization assessment
    (Workflow A's output) for one run -- never computes one. Returns
    None if nothing has been persisted yet for this run, or for the
    requested day specifically.
    """
    from app.services.stress_assessment.service import InvalidDayError

    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")
    if day is not None and not (1 <= day <= run.duration_days):
        raise InvalidDayError(
            f"day must be between 1 and {run.duration_days} for simulation run {run_id}"
        )

    query = db.query(OptimizationHistory).filter(OptimizationHistory.simulation_run_id == run_id)
    row = (
        query.filter(OptimizationHistory.day == day).first()
        if day is not None
        else query.order_by(OptimizationHistory.day.desc()).first()
    )
    if row is None:
        return None

    return _optimization_from_dict(json.loads(row.optimization_json))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.optimization.history",
        description=(
            "KAVACH Phase 6 backend processing (Workflow A): compute and "
            "persist daily optimization history for a completed simulation run."
        ),
    )
    parser.add_argument("--run-id", type=int, required=True)
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            count = persist_run_optimizations(db, args.run_id)
        except RunNotFoundError as e:
            print(f"✗ {e}")
            return 1
        print(f"✓ Persisted {count} daily optimization record(s) for simulation run {args.run_id}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
