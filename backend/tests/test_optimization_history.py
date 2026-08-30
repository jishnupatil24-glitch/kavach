"""
Phase 6 history tests: idempotent persistence, round-trip fidelity
against a live compute, nonexistent-run handling.
"""
from __future__ import annotations

import inspect

import pytest

from app.database.session import SessionLocal
from app.services.decision_engine.seed_parameters import ensure_decision_engine_parameters
from app.services.optimization import history as history_module
from app.services.optimization.farm_config import upsert_farm_configuration
from app.services.optimization.history import get_stored_optimization, persist_run_optimizations
from app.services.optimization.seed_parameters import ensure_optimization_parameters
from app.services.optimization.service import RunNotFoundError, optimize_run
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run


@pytest.fixture(scope="session")
def history_params_seeded(seeded_agronomics_db):
    db = SessionLocal()
    try:
        ensure_decision_engine_parameters(db)
        ensure_optimization_parameters(db)
    finally:
        db.close()


def test_persist_writes_one_row_per_day(history_params_seeded):
    from app.models.optimization_history import OptimizationHistory

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=12, scenario="normal", seed=201))
        count = persist_run_optimizations(db, run.id)
        assert count == 12
        assert db.query(OptimizationHistory).filter(OptimizationHistory.simulation_run_id == run.id).count() == 12
    finally:
        db.close()


def test_persist_is_idempotent(history_params_seeded):
    from app.models.optimization_history import OptimizationHistory

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=6, scenario="normal", seed=202))
        persist_run_optimizations(db, run.id)
        persist_run_optimizations(db, run.id)
        assert db.query(OptimizationHistory).filter(OptimizationHistory.simulation_run_id == run.id).count() == 6
    finally:
        db.close()


def test_persist_nonexistent_run_raises(history_params_seeded):
    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            persist_run_optimizations(db, 999999999)
    finally:
        db.close()


def test_get_stored_optimization_none_when_absent(history_params_seeded):
    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=203))
        from app.models.optimization_history import OptimizationHistory
        db.query(OptimizationHistory).filter(OptimizationHistory.simulation_run_id == run.id).delete()
        db.commit()
        assert get_stored_optimization(db, run.id) is None
    finally:
        db.close()


def test_get_stored_optimization_nonexistent_run_raises(history_params_seeded):
    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            get_stored_optimization(db, 999999999)
    finally:
        db.close()


def test_round_trip_identical_to_live_compute(history_params_seeded):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=95, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=70, scenario_duration_days=15,
        )
        run = create_run(db, config)
        upsert_farm_configuration(db, run.id, field_area=1, field_area_unit="acre", plant_population=8000)
        persist_run_optimizations(db, run.id)

        stored = get_stored_optimization(db, run.id, day=77)
        live = optimize_run(db, run.id, day=77)
        assert stored == live
    finally:
        db.close()


def test_history_module_never_touches_simulator_generation_files():
    source = inspect.getsource(history_module)
    forbidden = [
        "app.services.simulator.generator", "app.services.simulator.causal_model",
        "app.services.simulator.calibration", "app.services.simulator.scenarios",
        "routes.simulator", "simulator_cli", "create_run(",
    ]
    for fragment in forbidden:
        assert fragment not in source, f"history module references {fragment!r}"
