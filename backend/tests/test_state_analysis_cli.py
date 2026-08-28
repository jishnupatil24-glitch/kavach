from app import state_analysis_cli
from app.database.session import SessionLocal
from app.models.state_analysis_history import StateAnalysisHistory
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis.history import persist_run_history


def _make_run(duration_days=40, scenario="normal", seed=1, **kwargs):
    """
    A real Phase 2 run via the actual common creation path
    (run_service.create_run). Under the automatic-trigger integration
    this ALREADY persists Phase 3 history as a side effect -- it is no
    longer possible to create a run through the normal path without
    that happening (by design; see run_service.create_run).
    """
    db = SessionLocal()
    try:
        config = build_config(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
        return create_run(db, config)
    finally:
        db.close()


def _make_persisted_run(duration_days=40, scenario="normal", seed=1, **kwargs):
    """
    Same as _make_run -- kept as a separate name for tests that want to
    read explicitly-persisted history, even though persistence now
    happens automatically. Calling persist_run_history again here is
    redundant but harmless (idempotent).
    """
    run = _make_run(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
    db = SessionLocal()
    try:
        persist_run_history(db, run.id)
    finally:
        db.close()
    return run


def _make_run_with_history_removed(duration_days=40, scenario="normal", seed=1, **kwargs):
    """
    Simulates "nothing persisted yet" -- a state the automatic-trigger
    integration no longer produces on its own, but Workflow B (the CLI)
    must still handle honestly if it ever occurs (e.g. a run created
    before this integration existed, or a history row removed by hand).
    """
    run = _make_run(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
    db = SessionLocal()
    try:
        db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).delete()
        db.commit()
    finally:
        db.close()
    return run


def test_create_run_automatically_persists_phase3_history(seeded_db, seeded_agronomics_db):
    """
    The core new requirement: creating a run through the normal path
    (no manual `python -m app.services.state_analysis.history` call)
    must already have Phase 3 daily history available immediately
    afterward.
    """
    run = _make_run(duration_days=25, seed=9)
    db = SessionLocal()
    try:
        count = (
            db.query(StateAnalysisHistory)
            .filter(StateAnalysisHistory.simulation_run_id == run.id)
            .count()
        )
        assert count == 25
    finally:
        db.close()


def test_cli_refuses_to_compute_and_reports_when_nothing_persisted_yet(seeded_db, seeded_agronomics_db, capsys):
    """
    Workflow B must never fall back to computing analysis itself --
    it only reads Workflow A's stored output.
    """
    run = _make_run_with_history_removed(duration_days=10, seed=10)
    exit_code = state_analysis_cli.main(["--run-id", str(run.id)])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "No persisted Phase 3 analysis found" in out
    assert "app.services.state_analysis.history" in out


def test_cli_prints_full_analysis_for_a_persisted_run(seeded_db, seeded_agronomics_db, capsys):
    run = _make_persisted_run(duration_days=40, seed=11)
    exit_code = state_analysis_cli.main(["--run-id", str(run.id)])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "PHASE 3 STATE ANALYSIS" in out
    assert f"Simulation ID : {run.id}" in out
    assert "Analysis Day  : 40" in out
    assert "CURRENT STATE" in out
    assert "TREND PERSISTENCE" in out
    assert "ICAR REFERENCE COMPARISON" in out
    assert "CROP-STAGE CONTEXT" in out
    assert "AGRONOMIC CONTEXT" in out
    assert "DATA QUALITY" in out
    assert "STATE ANALYSIS SUMMARY" in out
    for label in ("Temperature", "Humidity", "Soil Moisture", "DLI", "Soil N", "Soil P", "Soil K"):
        assert label in out


def test_cli_displays_the_daily_averaged_current_state(seeded_db, seeded_agronomics_db, capsys):
    """
    The CLI's CURRENT STATE table must show the day's averaged value,
    not a single raw 6-hour reading.
    """
    from app.models.sensor_observation import SensorObservation

    run = _make_persisted_run(duration_days=10, seed=1234)

    db = SessionLocal()
    try:
        raw = (
            db.query(SensorObservation)
            .filter(SensorObservation.simulation_run_id == run.id, SensorObservation.day == 10)
            .all()
        )
        expected_mean = sum(o.temperature_c for o in raw) / len(raw)
    finally:
        db.close()

    exit_code = state_analysis_cli.main(["--run-id", str(run.id)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert f"{expected_mean:.2f} °C" in out


def test_cli_day_flag_reads_the_matching_persisted_day(seeded_db, seeded_agronomics_db, capsys):
    run = _make_persisted_run(duration_days=40, seed=12)

    exit_code = state_analysis_cli.main(["--run-id", str(run.id), "--day", "20"])
    assert exit_code == 0
    out20 = capsys.readouterr().out
    assert "Analysis Day  : 20" in out20

    exit_code = state_analysis_cli.main(["--run-id", str(run.id), "--day", "30"])
    assert exit_code == 0
    out30 = capsys.readouterr().out
    assert "Analysis Day  : 30" in out30

    assert out20 != out30


def test_cli_day_flag_does_not_populate_the_database(seeded_db, seeded_agronomics_db, capsys):
    """
    --day is view/filter only. It must never be what causes the
    backend history to get built -- even when history is genuinely
    absent, running the CLI with --day must not create it.
    """
    run = _make_run_with_history_removed(duration_days=10, seed=16)
    exit_code = state_analysis_cli.main(["--run-id", str(run.id), "--day", "5"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "No persisted Phase 3 analysis found" in out

    db = SessionLocal()
    try:
        count = db.query(StateAnalysisHistory).filter(
            StateAnalysisHistory.simulation_run_id == run.id
        ).count()
        assert count == 0
    finally:
        db.close()


def test_cli_nonexistent_run_fails_cleanly(seeded_db, seeded_agronomics_db, capsys):
    exit_code = state_analysis_cli.main(["--run-id", "9999999"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "No simulation run found" in out


def test_cli_out_of_range_day_fails_cleanly(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=10, seed=13)  # run-existence + day-range check needs no persistence
    exit_code = state_analysis_cli.main(["--run-id", str(run.id), "--day", "999"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "must be between 1 and 10" in out


def test_cli_missing_run_id_is_rejected_by_argparse():
    import pytest

    with pytest.raises(SystemExit):
        state_analysis_cli.main([])


def test_cli_day_100_overlap_shown_for_full_length_run(seeded_db, seeded_agronomics_db, capsys):
    run = _make_persisted_run(duration_days=120, seed=14)
    exit_code = state_analysis_cli.main(["--run-id", str(run.id), "--day", "100"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "kc_mid_stage" in out
    assert "kc_late_stage" in out
    assert "overlap" in out.lower()


def test_cli_ordinary_day_does_not_falsely_claim_an_overlap(seeded_db, seeded_agronomics_db, capsys):
    """
    Regression: full_cycle (Day 1-120) always matches alongside exactly
    one Kc sub-stage on any ordinary day -- that pairing is expected
    multiplicity, not the genuine day-100 source-range overlap, and
    must never be reported as one.
    """
    run = _make_persisted_run(duration_days=120, seed=17)
    for day in (1, 30, 60, 90, 120):
        exit_code = state_analysis_cli.main(["--run-id", str(run.id), "--day", str(day)])
        assert exit_code == 0
        out = capsys.readouterr().out
        assert "overlap" not in out.lower(), f"false overlap note on day {day}"


def test_cli_no_raw_python_objects_in_output(seeded_db, seeded_agronomics_db, capsys):
    run = _make_persisted_run(duration_days=5, seed=15)
    state_analysis_cli.main(["--run-id", str(run.id)])
    out = capsys.readouterr().out
    assert "object at 0x" not in out
    assert "TrendResult(" not in out
    assert "StateAnalysis(" not in out


def test_cli_reuses_existing_state_analysis_service_not_a_reimplementation():
    import inspect

    source = inspect.getsource(state_analysis_cli)
    forbidden_fragments = [
        "def compute_trend(",
        "def compute_persistence(",
        "def compute_icar_deviation(",
        "def resolve_crop_stages(",
        "def analyze_run(",
        "def persist_run_history(",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source, f"CLI appears to duplicate analysis logic: {fragment!r} found"
    assert "from app.services.state_analysis.history import get_stored_analysis" in source
    # Workflow B must never import Workflow A's per-day compute entrypoint.
    assert "from app.services.state_analysis.service import" in source
    assert "analyze_run" not in source.split("\"\"\"", 2)[-1]  # ignore the module docstring's own mention
