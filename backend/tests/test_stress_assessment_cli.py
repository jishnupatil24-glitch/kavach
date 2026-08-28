from app import stress_assessment_cli
from app.database.session import SessionLocal
from app.models.problem_assessment_history import ProblemAssessmentHistory
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run


def _make_run(duration_days=20, scenario="normal", seed=1, **kwargs):
    db = SessionLocal()
    try:
        config = build_config(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
        return create_run(db, config)  # already auto-persists Phase 3 + Phase 4 history
    finally:
        db.close()


def test_cli_prints_full_assessment_for_an_automatically_persisted_run(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=20, seed=6001)
    exit_code = stress_assessment_cli.main(["--run-id", str(run.id)])
    assert exit_code == 0

    out = capsys.readouterr().out
    assert "PHASE 4 PROBLEM ASSESSMENT" in out
    assert f"Simulation ID  : {run.id}" in out
    assert "Assessment Day : 20" in out
    assert "CROP-STAGE CONTEXT" in out
    assert "PROBLEM ASSESSMENTS" in out
    assert "EVIDENCE DETAIL" in out
    assert "PHASE 5 CANDIDATE PROBLEMS" in out
    for label in (
        "Water Depletion", "Excessive Moisture", "Heat-Related", "Temperature Deficit",
        "Low Humidity", "High Humidity", "Nitrogen-Related", "Phosphorus-Related",
        "Potassium-Related", "Light Deficit",
    ):
        assert label in out


def test_phase5_candidate_section_shows_status_and_severity(seeded_db, seeded_agronomics_db, capsys):
    """
    The PHASE 5 CANDIDATE PROBLEMS line for each candidate must show
    both the persisted status and the persisted severity -- reading the
    exact already-computed values, never recalculating anything.
    """
    from app.services.stress_assessment.history import get_stored_assessment

    run = _make_run(
        duration_days=25, scenario="heatwave", seed=6020,
        severity="severe", scenario_start_day=2, scenario_duration_days=20,
    )
    db = SessionLocal()
    try:
        stored = get_stored_assessment(db, run.id, day=20)
        evidenced = stored.evidenced_problems()
    finally:
        db.close()

    assert evidenced, "test setup must produce at least one evidenced problem to check the format"

    exit_code = stress_assessment_cli.main(["--run-id", str(run.id), "--day", "20"])
    assert exit_code == 0
    out = capsys.readouterr().out

    for p in evidenced:
        assert f"  - {p.label} ({p.status}, {p.severity})" in out


def test_phase5_candidate_section_none_case_unaffected(seeded_db, seeded_agronomics_db, capsys):
    # Day 1 never has enough history for a determined trend (Phase 3
    # needs >=3 days) -- every category is insufficient_data/no_evidence,
    # so evidenced_problems() is guaranteed empty. Confirms the "None."
    # formatting path still works unchanged after this edit.
    run = _make_run(duration_days=5, seed=6021)
    exit_code = stress_assessment_cli.main(["--run-id", str(run.id), "--day", "1"])
    assert exit_code == 0
    out = capsys.readouterr().out
    section = out.split("PHASE 5 CANDIDATE PROBLEMS")[1]
    assert "None." in section


def test_cli_shows_evidence_trail_for_a_severe_heatwave(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(
        duration_days=30, scenario="heatwave", seed=6002,
        severity="severe", scenario_start_day=3, scenario_duration_days=20,
    )
    exit_code = stress_assessment_cli.main(["--run-id", str(run.id), "--day", "20"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "[Heat-Related]" in out
    assert "Trend: RISING" in out
    assert "Persistence:" in out
    assert "ICAR:" in out
    assert "Today's raw 6-hour range" in out
    assert "not used as an independent stress signal" in out


def test_cli_never_populates_history_it_just_reads(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=10, seed=6003)
    db = SessionLocal()
    try:
        before = (
            db.query(ProblemAssessmentHistory)
            .filter(ProblemAssessmentHistory.simulation_run_id == run.id)
            .count()
        )
    finally:
        db.close()
    assert before == 10  # already auto-persisted by create_run

    stress_assessment_cli.main(["--run-id", str(run.id)])
    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "5"])
    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "7"])

    db = SessionLocal()
    try:
        after = (
            db.query(ProblemAssessmentHistory)
            .filter(ProblemAssessmentHistory.simulation_run_id == run.id)
            .count()
        )
    finally:
        db.close()
    assert after == 10  # CLI reads only -- no new/duplicate rows from 3 CLI invocations


def test_cli_refuses_and_names_backfill_command_when_history_absent(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=10, seed=6004)
    db = SessionLocal()
    try:
        db.query(ProblemAssessmentHistory).filter(ProblemAssessmentHistory.simulation_run_id == run.id).delete()
        db.commit()
    finally:
        db.close()

    exit_code = stress_assessment_cli.main(["--run-id", str(run.id)])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out
    assert "No persisted Phase 4 assessment found" in out
    assert "app.services.stress_assessment.history" in out


def test_cli_nonexistent_run_fails_cleanly(seeded_db, seeded_agronomics_db, capsys):
    exit_code = stress_assessment_cli.main(["--run-id", "9999999"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out


def test_cli_day_flag_reads_matching_persisted_day(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=20, seed=6005)
    exit_code = stress_assessment_cli.main(["--run-id", str(run.id), "--day", "12"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "Assessment Day : 12" in out


def test_cli_no_raw_python_objects_in_output(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=5, seed=6006)
    stress_assessment_cli.main(["--run-id", str(run.id)])
    out = capsys.readouterr().out
    assert "object at 0x" not in out
    assert "ProblemAssessment(" not in out
    assert "StressAssessment(" not in out


def test_cli_reuses_get_stored_assessment_not_a_reimplementation():
    import inspect

    source = inspect.getsource(stress_assessment_cli)
    forbidden_fragments = [
        "def compute_problem_assessment(",
        "def assess_run(",
        "def persist_run_assessments(",
        "AgronomicParameter",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source, f"CLI appears to duplicate logic: {fragment!r} found"
    assert "from app.services.stress_assessment.history import get_stored_assessment" in source


# ---------------------------------------------------------------------
# --show-pipeline mode
# ---------------------------------------------------------------------

def test_show_pipeline_displays_all_three_layers(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=20, seed=6010)
    exit_code = stress_assessment_cli.main(["--run-id", str(run.id), "--day", "15", "--show-pipeline"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PHASE 2 -> PHASE 3 -> PHASE 4 PIPELINE" in out
    assert "PHASE 2 -- RAW SENSOR READINGS" in out
    assert "PHASE 3 -- STATE ANALYSIS" in out
    assert "PHASE 4 -- PROBLEM ASSESSMENT + EVIDENCE + SEVERITY" in out
    assert "00:00" in out and "06:00" in out and "12:00" in out and "18:00" in out
    for label in ("Temperature", "Humidity", "Soil Moisture", "DLI", "Soil N", "Soil P", "Soil K"):
        assert label in out


def test_show_pipeline_raw_readings_match_actual_sensor_observations(seeded_db, seeded_agronomics_db, capsys):
    from app.models.sensor_observation import SensorObservation

    run = _make_run(duration_days=20, seed=6011)
    db = SessionLocal()
    try:
        raw = (
            db.query(SensorObservation)
            .filter(SensorObservation.simulation_run_id == run.id, SensorObservation.day == 10)
            .all()
        )
        expected_temps = sorted(round(o.temperature_c, 2) for o in raw)
    finally:
        db.close()

    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "10", "--show-pipeline"])
    out = capsys.readouterr().out
    for t in expected_temps:
        assert f"{t:.2f}" in out


def test_show_pipeline_phase3_section_matches_stored_phase3_state(seeded_db, seeded_agronomics_db, capsys):
    from app.services.state_analysis.history import get_stored_analysis

    run = _make_run(duration_days=20, seed=6012)
    db = SessionLocal()
    try:
        phase3 = get_stored_analysis(db, run.id, day=15)
        temp = next(pa for pa in phase3.parameters if pa.current.field == "temperature_c")
    finally:
        db.close()

    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "15", "--show-pipeline"])
    out = capsys.readouterr().out
    assert f"{temp.current.value:.2f} °C" in out
    assert temp.trend.direction in out


def test_show_pipeline_severity_matches_stored_phase4_severity(seeded_db, seeded_agronomics_db, capsys):
    from app.services.stress_assessment.history import get_stored_assessment

    run = _make_run(
        duration_days=25, scenario="heatwave", seed=6013,
        severity="severe", scenario_start_day=2, scenario_duration_days=20,
    )
    db = SessionLocal()
    try:
        stored = get_stored_assessment(db, run.id, day=20)
        heat = next(p for p in stored.problems if p.category == "heat_related")
    finally:
        db.close()

    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "20", "--show-pipeline"])
    out = capsys.readouterr().out
    assert f"severity: {heat.severity}" in out


def test_show_pipeline_is_read_only(seeded_db, seeded_agronomics_db, capsys):
    from app.models.sensor_observation import SensorObservation
    from app.models.state_analysis_history import StateAnalysisHistory

    run = _make_run(duration_days=15, seed=6014)
    db = SessionLocal()
    try:
        obs_before = db.query(SensorObservation).filter(SensorObservation.simulation_run_id == run.id).count()
        p3_before = db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).count()
        p4_before = db.query(ProblemAssessmentHistory).filter(ProblemAssessmentHistory.simulation_run_id == run.id).count()
    finally:
        db.close()

    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "10", "--show-pipeline"])
    stress_assessment_cli.main(["--run-id", str(run.id), "--show-pipeline"])

    db = SessionLocal()
    try:
        obs_after = db.query(SensorObservation).filter(SensorObservation.simulation_run_id == run.id).count()
        p3_after = db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).count()
        p4_after = db.query(ProblemAssessmentHistory).filter(ProblemAssessmentHistory.simulation_run_id == run.id).count()
        total_runs_after = db.query(ProblemAssessmentHistory.simulation_run_id).distinct().count()
    finally:
        db.close()

    assert obs_before == obs_after
    assert p3_before == p3_after
    assert p4_before == p4_after


def test_show_pipeline_does_not_regenerate_simulation(seeded_db, seeded_agronomics_db, capsys):
    from app.models.simulation_run import SimulationRun

    run = _make_run(duration_days=10, seed=6015)
    db = SessionLocal()
    try:
        run_count_before = db.query(SimulationRun).count()
    finally:
        db.close()

    stress_assessment_cli.main(["--run-id", str(run.id), "--show-pipeline"])
    stress_assessment_cli.main(["--run-id", str(run.id), "--day", "5", "--show-pipeline"])

    db = SessionLocal()
    try:
        run_count_after = db.query(SimulationRun).count()
    finally:
        db.close()
    assert run_count_before == run_count_after


def test_show_pipeline_no_raw_python_objects_in_output(seeded_db, seeded_agronomics_db, capsys):
    run = _make_run(duration_days=10, seed=6016)
    stress_assessment_cli.main(["--run-id", str(run.id), "--show-pipeline"])
    out = capsys.readouterr().out
    assert "object at 0x" not in out
    assert "StateAnalysis(" not in out
    assert "SensorObservation(" not in out


def test_cli_structural_no_calculation_logic_even_with_show_pipeline():
    import inspect

    source = inspect.getsource(stress_assessment_cli)
    forbidden_fragments = [
        "def compute_trend(", "def compute_persistence(", "def compute_icar_deviation(",
        "def analyze_run(", "STABILITY_K", "def _compute_severity(",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source, f"CLI appears to duplicate logic: {fragment!r} found"
    assert "from app.services.state_analysis.history import get_stored_analysis" in source
