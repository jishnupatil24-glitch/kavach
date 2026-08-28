"""
Workflow A tests: backend persistence of Phase 3 state history for an
entire completed simulation run, independent of the Phase 3 CLI
(Workflow B), which has its own tests in test_state_analysis_cli.py.
"""
from __future__ import annotations

import inspect

import pytest

from app.database.session import SessionLocal
from app.models.state_analysis_history import StateAnalysisHistory
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis import history as history_module
from app.services.state_analysis.history import get_stored_analysis, persist_run_history
from app.services.state_analysis.service import InvalidDayError, RunNotFoundError, analyze_run


def _make_run(db, duration_days=60, scenario="normal", seed=1, **kwargs):
    config = build_config(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
    return create_run(db, config)


def test_persist_writes_exactly_one_row_per_day():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=60, seed=1001)
        count = persist_run_history(db, run.id)
        assert count == 60

        stored_days = (
            db.query(StateAnalysisHistory.day)
            .filter(StateAnalysisHistory.simulation_run_id == run.id)
            .all()
        )
        assert sorted(d for (d,) in stored_days) == list(range(1, 61))
    finally:
        db.close()


def test_persist_is_idempotent_on_rerun():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=20, seed=1002)
        count1 = persist_run_history(db, run.id)
        count2 = persist_run_history(db, run.id)
        assert count1 == count2 == 20

        total_rows = (
            db.query(StateAnalysisHistory)
            .filter(StateAnalysisHistory.simulation_run_id == run.id)
            .count()
        )
        assert total_rows == 20  # no duplicates from the second run
    finally:
        db.close()


def test_persist_nonexistent_run_raises():
    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            persist_run_history(db, 9_999_999)
    finally:
        db.close()


def test_get_stored_analysis_returns_none_when_history_is_absent():
    """
    Under the automatic-trigger integration, create_run() itself always
    calls persist_run_history() -- so "nothing persisted yet" can no
    longer be reached by simply creating a run. This test instead
    removes the auto-created rows directly (simulating any situation
    where history is genuinely missing, e.g. a pre-integration run)
    and confirms get_stored_analysis() still reports that honestly
    rather than computing a fallback.
    """
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=1003)
        db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).delete()
        db.commit()

        assert get_stored_analysis(db, run.id) is None
        assert get_stored_analysis(db, run.id, day=5) is None
    finally:
        db.close()


def test_get_stored_analysis_invalid_day_raises_even_without_persisting():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=1004)
        with pytest.raises(InvalidDayError):
            get_stored_analysis(db, run.id, day=999)
    finally:
        db.close()


def test_get_stored_analysis_nonexistent_run_raises():
    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            get_stored_analysis(db, 9_999_999)
    finally:
        db.close()


def test_get_stored_analysis_defaults_to_latest_persisted_day():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=15, seed=1005)
        persist_run_history(db, run.id)
        result = get_stored_analysis(db, run.id)
        assert result.analysis_day == 15
    finally:
        db.close()


def test_stored_analysis_round_trips_exactly_against_live_analyze_run():
    """
    The persisted-and-reloaded StateAnalysis must be numerically
    identical to what analyze_run() itself would compute for that same
    day -- persistence is a cache of the exact same calculation, never
    a second, independently derived value.
    """
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=35, seed=1006)
        persist_run_history(db, run.id)

        live = analyze_run(db, run.id, day=30)
        stored = get_stored_analysis(db, run.id, day=30)

        assert stored.analysis_day == live.analysis_day
        assert stored.crop == live.crop
        for live_pa, stored_pa in zip(live.parameters, stored.parameters):
            assert live_pa.current.value == stored_pa.current.value
            assert live_pa.current.day == stored_pa.current.day
            assert live_pa.trend.direction == stored_pa.trend.direction
            assert live_pa.trend.rate_per_day == stored_pa.trend.rate_per_day
            assert live_pa.persistence.days == stored_pa.persistence.days
            assert live_pa.icar.signed_difference == stored_pa.icar.signed_difference

        live_stage_names = sorted(s.name for s in live.crop_stages)
        stored_stage_names = sorted(s.name for s in stored.crop_stages)
        assert live_stage_names == stored_stage_names

        live_context = sorted((i.parameter_name, i.value_display) for i in live.agronomic_context)
        stored_context = sorted((i.parameter_name, i.value_display) for i in stored.agronomic_context)
        assert live_context == stored_context

        assert live.data_quality_notes == stored.data_quality_notes
    finally:
        db.close()


def test_legacy_format_row_reads_without_crashing_and_is_flagged():
    """
    Backward compatibility: a state_analysis_history row persisted
    before the daily-aggregation change stored `current` with `hour`
    (no `n_readings`/`note`). get_stored_analysis must still read it
    (not crash) and must say plainly that the value predates the
    current daily-average definition -- never silently present it as
    an up-to-date daily average.
    """
    import json

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=5, seed=1010)

        legacy_current = {
            "parameter": "Temperature", "field": "temperature_c",
            "value": 25.5, "day": 5, "hour": 18,
        }
        legacy_trend = {
            "parameter": "Temperature", "direction": "STABLE", "rate_per_day": 0.1,
            "rate_unit": "°C/day", "standard_error_per_day": 0.05, "stable_band": 0.1,
            "n_observations": 5, "note": None,
        }
        legacy_persistence = {"parameter": "Temperature", "direction": "STABLE", "days": 3, "note": None}
        legacy_icar = {
            "parameter": "Temperature", "current_value": 25.5, "icar_value": 25.0, "icar_day": 5,
            "signed_difference": 0.5, "absolute_difference": 0.5, "unit_suffix": " °C", "note": None,
        }

        db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).delete()
        db.add(
            StateAnalysisHistory(
                simulation_run_id=run.id,
                day=5,
                crop="tomato",
                parameters_json=json.dumps(
                    [{"current": legacy_current, "trend": legacy_trend,
                      "persistence": legacy_persistence, "icar": legacy_icar}]
                ),
                crop_stages_json=json.dumps([]),
                agronomic_context_json=json.dumps([]),
                data_quality_notes_json=json.dumps([]),
            )
        )
        db.commit()

        result = get_stored_analysis(db, run.id, day=5)
        assert result is not None
        temp = result.parameters[0]
        assert temp.current.value == 25.5
        assert temp.current.n_readings == 1
        assert temp.current.note is not None
        assert "LEGACY FORMAT" in temp.current.note
        assert "recompute" in temp.current.note.lower()
    finally:
        db.close()


def test_day_100_overlap_round_trips_through_persisted_json():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=120, seed=1007)
        persist_run_history(db, run.id)
        stored = get_stored_analysis(db, run.id, day=100)
        names = {s.name for s in stored.crop_stages}
        assert "kc_mid_stage" in names
        assert "kc_late_stage" in names
    finally:
        db.close()


def test_reruning_persist_after_more_history_would_exist_still_matches_duration():
    # persist_run_history always covers day 1..duration_days regardless
    # of how many times it has been called before.
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=8, seed=1008)
        persist_run_history(db, run.id)
        persist_run_history(db, run.id)
        rows = (
            db.query(StateAnalysisHistory)
            .filter(StateAnalysisHistory.simulation_run_id == run.id)
            .count()
        )
        assert rows == 8
    finally:
        db.close()


def test_history_module_entrypoint_persists_a_real_run(capsys):
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=12, seed=1009)
        run_id = run.id
    finally:
        db.close()

    exit_code = history_module.main(["--run-id", str(run_id)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "✓" in out
    assert "Persisted 12" in out

    db = SessionLocal()
    try:
        count = (
            db.query(StateAnalysisHistory)
            .filter(StateAnalysisHistory.simulation_run_id == run_id)
            .count()
        )
        assert count == 12
    finally:
        db.close()


def test_history_module_entrypoint_nonexistent_run_fails_cleanly(capsys):
    exit_code = history_module.main(["--run-id", "9999999"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "No simulation run found" in out


def test_history_module_never_imports_simulator_internals():
    source = inspect.getsource(history_module)
    forbidden_fragments = [
        "simulator.generator",
        "simulator.causal_model",
        "simulator.calibration",
        "simulator.scenarios",
        "simulator.rng",
        "simulator.constants",
        "simulation_internal_state",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source


def test_history_module_never_touches_phase2_files():
    """
    Workflow A is a standalone backend entrypoint -- it must not import
    or reference anything that would modify Phase 2's own generation
    call sites (run_service.create_run, routes/simulator.py,
    simulator_cli.py). It's allowed to READ SimulationRun.
    """
    code = inspect.getsource(history_module).split('"""', 2)[-1]  # skip the module docstring
    assert "app.routes.simulator" not in code
    assert "app.simulator_cli" not in code
    assert "def create_run(" not in code
