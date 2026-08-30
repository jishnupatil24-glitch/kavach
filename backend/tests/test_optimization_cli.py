"""
Phase 6 CLI tests: presentation-only, read-only, structural guards
that it never recomputes/duplicates optimization logic and never
writes farm configuration or history.
"""
from __future__ import annotations

import inspect

import pytest

from app import optimization_cli
from app.database.session import SessionLocal
from app.services.decision_engine.seed_parameters import ensure_decision_engine_parameters
from app.services.optimization.farm_config import upsert_farm_configuration
from app.services.optimization.history import persist_run_optimizations
from app.services.optimization.seed_parameters import ensure_optimization_parameters
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run


@pytest.fixture(scope="session")
def cli_params_seeded(seeded_agronomics_db):
    db = SessionLocal()
    try:
        ensure_decision_engine_parameters(db)
        ensure_optimization_parameters(db)
    finally:
        db.close()


def test_cli_reuses_stored_history_not_a_reimplementation():
    source = inspect.getsource(optimization_cli)
    forbidden_fragments = [
        "def optimize_water(", "def optimize_nutrient(", "def optimize_run(",
        "def persist_run_optimizations(", "def upsert_farm_configuration(",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source, f"CLI appears to duplicate logic: {fragment!r} found"
    assert "from app.services.optimization.history import get_stored_optimization" in source
    assert "optimize_run" not in source.split('"""', 2)[-1]  # ignore the module docstring's own mention


def test_cli_never_imports_farm_config_writer():
    source = inspect.getsource(optimization_cli)
    assert "upsert_farm_configuration" not in source


def test_cli_refuses_and_names_backfill_command_when_absent(cli_params_seeded, capsys):
    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=101))
        from app.models.optimization_history import OptimizationHistory
        db.query(OptimizationHistory).filter(OptimizationHistory.simulation_run_id == run.id).delete()
        db.commit()

        exit_code = optimization_cli.fetch_and_print(db, run.id, None)
        assert exit_code == 1
        out = capsys.readouterr().out
        assert "python -m app.services.optimization.history" in out
    finally:
        db.close()


def test_cli_prints_full_assessment_for_persisted_run(cli_params_seeded, capsys):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=95, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=70, scenario_duration_days=15,
        )
        run = create_run(db, config)
        upsert_farm_configuration(db, run.id, field_area=1, field_area_unit="acre", plant_population=8000)
        persist_run_optimizations(db, run.id)

        exit_code = optimization_cli.fetch_and_print(db, run.id, 77)
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "KAVACH -- HISTORICAL OPTIMIZATION" in out
        assert "Simulation day 77" in out
        assert "BASELINE" in out
        assert "WATER SAVINGS" in out
        assert "RESOURCE FEASIBILITY" in out
        assert "PROVENANCE" in out
        assert "3.50 L/plant/day" in out
    finally:
        db.close()


def test_cli_current_mode_banner_and_latest_day(cli_params_seeded, capsys):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=95, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=70, scenario_duration_days=15,
        )
        run = create_run(db, config)
        upsert_farm_configuration(db, run.id, field_area=1, field_area_unit="acre", plant_population=8000)
        persist_run_optimizations(db, run.id)

        exit_code = optimization_cli.fetch_and_print(db, run.id, None)
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "KAVACH -- CURRENT OPTIMIZED ACTION PLAN" in out
        assert f"Simulation day {run.duration_days}" in out
        assert "(latest available)" in out
    finally:
        db.close()


def test_cli_historical_mode_banner_has_no_latest_marker(cli_params_seeded, capsys):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=95, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=70, scenario_duration_days=15,
        )
        run = create_run(db, config)
        upsert_farm_configuration(db, run.id, field_area=1, field_area_unit="acre", plant_population=8000)
        persist_run_optimizations(db, run.id)

        exit_code = optimization_cli.fetch_and_print(db, run.id, 77)
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "KAVACH -- HISTORICAL OPTIMIZATION" in out
        assert "(latest available)" not in out
    finally:
        db.close()


def test_cli_current_and_historical_share_the_same_fetch_function():
    # Both modes call the exact same function -- no duplicated CLI logic path.
    import inspect
    source = inspect.getsource(optimization_cli.main)
    assert source.count("fetch_and_print(") == 1


def test_cli_shows_no_farm_configuration_message_when_absent(cli_params_seeded, capsys):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)
        exit_code = optimization_cli.fetch_and_print(db, run.id, 34)
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "No farm configuration exists for this run." in out
        assert "python -m app.services.optimization.farm_config" in out
    finally:
        db.close()


def test_cli_nonexistent_run_fails_cleanly(cli_params_seeded, capsys):
    db = SessionLocal()
    try:
        exit_code = optimization_cli.fetch_and_print(db, 999999999, None)
        assert exit_code == 1
        out = capsys.readouterr().out
        assert out.startswith("✗")
    finally:
        db.close()
