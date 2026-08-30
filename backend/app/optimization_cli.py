"""
WORKFLOW B -- presentation-only terminal front-end for Phase 6.
Contains ZERO optimization logic of its own. It reads and formats
ALREADY-PERSISTED/ALREADY-STORED data via:
  - app.services.optimization.history.get_stored_optimization
    (Phase 6's own persisted history -- never calls optimize_run())
  - app.services.decision_engine.history.get_stored_decision
    (Phase 5's own persisted history, for the PHASE 5 INPUT section --
    never calls decide_run())

This CLI is STRICTLY READ-ONLY: it never recomputes Phase 3/4/5, never
modifies farm configuration (use
`python -m app.services.optimization.farm_config` for that -- a
separate write/setter workflow, deliberately not mixed in here), never
silently creates missing farm configuration, and never writes history.
If nothing has been persisted yet for the requested run/day, this CLI
says so and stops -- use
`python -m app.services.optimization.history --run-id N` (Workflow A)
to build/refresh that history first.

Two modes, same underlying service call (`get_stored_optimization`),
no duplicated optimization logic between them -- only the CLI's own
presentation (header/framing) differs:

  CURRENT (no --day):   the primary farmer-facing mode. Omitting --day
      passes day=None through to get_stored_optimization/
      get_stored_decision, both of which ALREADY default to the LATEST
      persisted day for the run (an existing behavior of this
      project's history-read functions, not a new concept introduced
      here) -- i.e. "what should the farmer do right now, given the
      most recently detected state." "Current" means latest stored
      simulation state, never wall-clock time -- this is a simulation.

  HISTORICAL (--day N):  explicitly optimizes the stored Phase 5
      decision for assessment day N. For debugging, reproducibility,
      and demonstration -- not the primary workflow.

Usage:
    python -m app.optimization_cli --run-id 584          (current)
    python -m app.optimization_cli --run-id 584 --day 40 (historical)
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
from app.services.decision_engine.validation import OUTCOME_ACTION_RECOMMENDED
from app.services.optimization.history import get_stored_optimization
from app.services.optimization.service import OptimizationAssessment, StateAnalysisError

WIDTH = 78


def fail(message: str) -> None:
    print(f"✗ {message}")


def _fmt(value, unit: str = "", precision: int = 2) -> str:
    if value is None:
        return "UNAVAILABLE"
    return f"{value:,.{precision}f}{unit}"


def print_header(assessment: OptimizationAssessment, historical: bool) -> None:
    print("=" * WIDTH)
    if historical:
        print("KAVACH -- HISTORICAL OPTIMIZATION".center(WIDTH))
    else:
        print("KAVACH -- CURRENT OPTIMIZED ACTION PLAN".center(WIDTH))
    print("=" * WIDTH)
    print()
    print(f"Simulation ID     : {assessment.run_id}")
    suffix = "" if historical else "  (latest available)"
    print(f"Assessment source : Simulation day {assessment.assessment_day}{suffix}")
    print(f"Crop              : {assessment.crop.capitalize()}")
    print()


def print_recommended_action(db, run_id: int, day: int) -> None:
    print("-" * WIDTH)
    print("RECOMMENDED ACTION (from Phase 5, stored -- not recomputed)")
    print("-" * WIDTH)
    print()
    decision = get_stored_decision(db, run_id, day=day)
    if decision is None:
        print("  (no persisted Phase 5 history found for this run/day)")
        print()
        return
    recommended = [d for d in decision.decisions if d.outcome == OUTCOME_ACTION_RECOMMENDED]
    if not recommended:
        print("  No action currently recommended.")
        print()
        return
    for d in recommended:
        print(f"Problem:\n    {d.label}\n")
        print(f"Evidence status:\n    {d.status}\n")
        print(f"Severity:\n    {d.severity}\n")
        print(f"Action:\n    {d.action_label}\n")
        print(f"Eligibility:\n    {d.outcome}\n")


def print_farm_configuration(assessment: OptimizationAssessment) -> None:
    print("-" * WIDTH)
    print("FARM CONFIGURATION")
    print("-" * WIDTH)
    print()
    fc = assessment.farm_configuration
    if not fc.exists:
        print("  No farm configuration exists for this run.")
        print("  Set one with: python -m app.services.optimization.farm_config --run-id "
              f"{assessment.run_id} --field-area <N> --field-area-unit <acre|hectare|m2>")
        print()
        return
    print(f"Field Area:\n    {fc.field_area:g} {fc.field_area_unit}\n")
    print(f"Irrigation System:\n    {fc.irrigation_system_type or 'not specified'}\n")


def _print_population(pop) -> None:
    print(f"Plant Population:\n    {pop.plants:,}" if pop.plants is not None else "Plant Population:\n    UNKNOWN")
    print(f"Population Source:\n    {pop.source}")
    print(f"    ({pop.note})")
    print()


def print_water_optimization(w) -> None:
    print("-" * WIDTH)
    print(f"WATER OPTIMIZATION -- {w.action_label} [{w.category}]")
    print("-" * WIDTH)
    print()
    _print_population(w.plant_population)

    print("BASELINE")
    print(f"    Stage: {w.stage_name or 'UNAVAILABLE'}")
    print(f"    Baseline irrigation (theoretical crop requirement): {_fmt(w.baseline_l_per_plant_day, ' L/plant/day')}")
    print(f"    Baseline field volume: {_fmt(w.baseline_l_per_day, ' L/day', 0)}")
    print()

    print("OPTIMIZED PLAN")
    print(f"    Severity: {w.severity}   Adjustment: {_fmt(w.adjustment_pct, '%', 0)} ({w.direction})")
    print(f"    Optimized irrigation: {_fmt(w.optimized_l_per_plant_day, ' L/plant/day')}")
    print(f"    Optimized field volume: {_fmt(w.optimized_l_per_day, ' L/day', 0)}")
    print(f"    Review cycle: {_fmt(w.review_cycle_days, ' days', 0)}")
    print()

    is_increase = w.direction == "increase"
    section_title = "WATER USE CHANGE" if is_increase else "WATER SAVINGS"
    print(f"{section_title} (theoretical crop requirement basis)")
    print(f"    Baseline:  {_fmt(w.baseline_l_per_day, ' L/day', 0)}")
    print(f"    Optimized: {_fmt(w.optimized_l_per_day, ' L/day', 0)}")
    if is_increase:
        extra = None if w.water_saved_l_per_day is None else -w.water_saved_l_per_day
        extra_pct = None if w.water_saving_percentage is None else -w.water_saving_percentage
        total = None if w.total_water_saved_liters is None else -w.total_water_saved_liters
        print(f"    Additional water required: {_fmt(extra, ' L/day', 0)}")
        print(f"    Increase:  {_fmt(extra_pct, '%', 1)}")
        print(f"    Total over review cycle: {_fmt(total, ' L', 0)}")
    else:
        print(f"    Saved:     {_fmt(w.water_saved_l_per_day, ' L/day', 0)}")
        print(f"    Saving:    {_fmt(w.water_saving_percentage, '%', 1)}")
        print(f"    Total over review cycle: {_fmt(w.total_water_saved_liters, ' L', 0)}")
    print()

    print("DELIVERED IRRIGATION (accounts for system efficiency -- NOT double-applied to the above)")
    print(f"    Efficiency: {_fmt(w.irrigation_efficiency_pct, '%', 0)} (source: {w.irrigation_efficiency_source})")
    print(f"    Delivered baseline:  {_fmt(w.delivered_baseline_l_per_day, ' L/day', 0)}")
    print(f"    Delivered optimized: {_fmt(w.delivered_optimized_l_per_day, ' L/day', 0)}")
    print()

    print("RESOURCE FEASIBILITY")
    for check in w.feasibility:
        print(f"    {check.label}: {check.status}  ({check.detail})")
    print()

    print("COST")
    if w.cost.status == "AVAILABLE":
        print(f"    Baseline:  {w.cost.baseline_cost:,.2f}")
        print(f"    Optimized: {w.cost.optimized_cost:,.2f}")
        print(f"    Change:    {w.cost.cost_change:+,.2f}")
    else:
        print(f"    COST: UNAVAILABLE -- {w.cost.detail}")
    print()

    print("EXPECTED OUTCOME")
    print(f"    Expected direction: {w.expected_direction}")
    print(f"    Basis: {w.expected_direction_basis}")
    print()

    print("PROVENANCE")
    print(f"    Baseline:  {w.baseline_provenance}")
    print(f"    Adjustment: {w.adjustment_provenance}")
    print(f"    Optimized quantity: {w.optimized_provenance}")
    print()

    if w.limitations:
        print("LIMITATIONS")
        for lim in w.limitations:
            print(f"    - {lim}")
        print()


def print_nutrient_optimization(n) -> None:
    print("-" * WIDTH)
    print(f"NUTRIENT OPTIMIZATION -- {n.action_label} [{n.category}] ({n.nutrient})")
    print("-" * WIDTH)
    print()
    _print_population(n.plant_population)

    print("BASELINE (SOURCED -- ICAR reference per-plant-per-day demand)")
    print(f"    Baseline: {_fmt(n.baseline_g_per_plant_day, ' g/plant/day')}")
    print()

    print("OPTIMIZED PLAN")
    print(f"    Severity: {n.severity}   Adjustment: {_fmt(n.adjustment_pct, '%', 0)} (direction: {n.direction})")
    print(f"    Direction basis: {n.direction_basis}")
    print(f"    Optimized: {_fmt(n.optimized_g_per_plant_day, ' g/plant/day')}")
    print(f"    Field total: {_fmt(n.total_kg_per_day, ' kg/day', 3)}")
    print(f"    Review cycle: {_fmt(n.duration_days, ' days', 0)}  Total quantity: {_fmt(n.total_quantity_kg, ' kg', 3)}")
    print()

    print("COST")
    if n.cost.status == "AVAILABLE":
        print(f"    Baseline:  {n.cost.baseline_cost:,.2f}")
        print(f"    Optimized: {n.cost.optimized_cost:,.2f}")
        print(f"    Change:    {n.cost.cost_change:+,.2f}")
    else:
        print(f"    COST: UNAVAILABLE -- {n.cost.detail}")
    print()

    print("EXPECTED OUTCOME")
    print(f"    Expected direction: {n.expected_direction}")
    print(f"    Basis: {n.expected_direction_basis}")
    print()

    print("PROVENANCE")
    print(f"    Baseline:  {n.baseline_provenance}")
    print(f"    Adjustment: {n.adjustment_provenance}")
    print(f"    Optimized quantity: {n.optimized_provenance}")
    print()

    if n.limitations:
        print("LIMITATIONS")
        for lim in n.limitations:
            print(f"    - {lim}")
        print()


def print_optimization_assessment(
    assessment: OptimizationAssessment, db=None, run_id: int | None = None, historical: bool = False,
) -> None:
    print_header(assessment, historical)
    if db is not None and run_id is not None:
        print_recommended_action(db, run_id, assessment.assessment_day)
    print_farm_configuration(assessment)

    if not assessment.water_optimizations and not assessment.nutrient_optimizations and not assessment.unsupported:
        print("  Nothing to optimize -- no currently recommended action has a Phase 6 outcome.")
        print()

    for w in assessment.water_optimizations:
        print_water_optimization(w)
    for n in assessment.nutrient_optimizations:
        print_nutrient_optimization(n)

    if assessment.unsupported:
        print("-" * WIDTH)
        print("QUALITATIVE-ONLY ACTIONS (no quantitative resource model)")
        print("-" * WIDTH)
        print()
        for u in assessment.unsupported:
            print(f"    {u.action_label or u.category} [{u.category}]: {u.reason}")
        print()

    if assessment.multi_action_note:
        print("-" * WIDTH)
        print("MULTIPLE ACTIONS")
        print("-" * WIDTH)
        print()
        print(f"    {assessment.multi_action_note}")
        print()

    print("-" * WIDTH)
    print("LIMITATIONS")
    print("-" * WIDTH)
    print()
    for lim in assessment.limitations:
        print(f"    {lim}")
    print()
    print("=" * WIDTH)


def fetch_and_print(db, run_id: int, day: int | None) -> int:
    try:
        assessment = get_stored_optimization(db, run_id, day=day)
    except StateAnalysisError as e:
        fail(str(e))
        return 1

    if assessment is None:
        day_clause = f" at day {day}" if day is not None else ""
        fail(
            f"No persisted Phase 6 optimization found for simulation run {run_id}{day_clause}. "
            f"Run `python -m app.services.optimization.history --run-id {run_id}` "
            "first to build the backend history."
        )
        return 1

    print_optimization_assessment(assessment, db=db, run_id=run_id, historical=day is not None)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.optimization_cli",
        description=(
            "KAVACH Phase 6 optimization CLI (read-only). Omit --day for the current "
            "optimized action plan (latest stored assessment); pass --day N for the "
            "historical optimization at a specific simulation day."
        ),
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument(
        "--day", type=int, default=None,
        help="Optional. Omit for current mode (latest stored assessment); pass a specific "
             "simulation day for historical mode.",
    )
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return fetch_and_print(db, args.run_id, args.day)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
