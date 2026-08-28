"""
Workflow A tests: backend persistence of Phase 4 problem-assessment
history for an entire simulation run, independent of the Phase 4 CLI
(Workflow B), which has its own tests in test_stress_assessment_cli.py.
"""
from __future__ import annotations

import inspect

import pytest

from app.database.session import SessionLocal
from app.models.problem_assessment_history import ProblemAssessmentHistory
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.stress_assessment import history as history_module
from app.services.stress_assessment.history import get_stored_assessment, persist_run_assessments
from app.services.stress_assessment.service import RunNotFoundError, assess_run


def _make_run(db, duration_days=20, scenario="normal", seed=1, **kwargs):
    config = build_config(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
    return create_run(db, config)


def test_run_creation_automatically_persists_one_row_per_day():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=25, seed=5001)  # create_run already calls persist_run_assessments
        count = (
            db.query(ProblemAssessmentHistory)
            .filter(ProblemAssessmentHistory.simulation_run_id == run.id)
            .count()
        )
        assert count == 25
        days = sorted(
            d for (d,) in db.query(ProblemAssessmentHistory.day)
            .filter(ProblemAssessmentHistory.simulation_run_id == run.id).all()
        )
        assert days == list(range(1, 26))
    finally:
        db.close()


def test_persist_is_idempotent_on_rerun():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=12, seed=5002)
        count1 = persist_run_assessments(db, run.id)
        count2 = persist_run_assessments(db, run.id)
        assert count1 == count2 == 12
        total = (
            db.query(ProblemAssessmentHistory)
            .filter(ProblemAssessmentHistory.simulation_run_id == run.id)
            .count()
        )
        assert total == 12
    finally:
        db.close()


def test_persist_nonexistent_run_raises():
    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            persist_run_assessments(db, 9_999_999)
    finally:
        db.close()


def test_get_stored_assessment_none_when_absent():
    from app.models.state_analysis_history import StateAnalysisHistory

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=5003)
        db.query(ProblemAssessmentHistory).filter(ProblemAssessmentHistory.simulation_run_id == run.id).delete()
        db.commit()
        assert get_stored_assessment(db, run.id) is None
        assert get_stored_assessment(db, run.id, day=5) is None
    finally:
        db.close()


def test_get_stored_assessment_nonexistent_run_raises():
    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            get_stored_assessment(db, 9_999_999)
    finally:
        db.close()


def test_get_stored_assessment_defaults_to_latest_persisted_day():
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=18, seed=5004)
        result = get_stored_assessment(db, run.id)
        assert result.assessment_day == 18
    finally:
        db.close()


def test_stored_assessment_round_trips_exactly_against_live_assess_run():
    db = SessionLocal()
    try:
        run = _make_run(
            db, duration_days=30, scenario="heatwave", seed=5005,
            severity="severe", scenario_start_day=3, scenario_duration_days=20,
        )
        live = assess_run(db, run.id, day=25)
        stored = get_stored_assessment(db, run.id, day=25)

        assert stored.assessment_day == live.assessment_day
        for live_p, stored_p in zip(live.problems, stored.problems):
            assert live_p.category == stored_p.category
            assert live_p.status == stored_p.status
            assert live_p.direction == stored_p.direction
            assert live_p.current_value == stored_p.current_value
            assert live_p.persistence_days == stored_p.persistence_days
            assert live_p.sourced_corroboration_notes == stored_p.sourced_corroboration_notes
    finally:
        db.close()


def test_history_module_entrypoint_persists_a_real_run(capsys):
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=9, seed=5006)
        run_id = run.id
    finally:
        db.close()

    exit_code = history_module.main(["--run-id", str(run_id)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "✓" in out
    assert "Persisted 9" in out


def test_history_module_entrypoint_nonexistent_run_fails_cleanly(capsys):
    exit_code = history_module.main(["--run-id", "9999999"])
    assert exit_code == 1
    out = capsys.readouterr().out
    assert "✗" in out


def test_legacy_format_row_without_severity_reads_without_crashing_and_is_flagged():
    """
    Backward compatibility: a problem_assessment_history row persisted
    before the severity feature existed had no "severity"/
    "severity_factors"/"severity_disclaimer" keys in its problems_json.
    get_stored_assessment must still read it (not crash) and must say
    plainly severity was never computed -- never silently present it as
    LOW/insufficient without explanation.
    """
    import json

    from app.services.stress_assessment.evidence import SEVERITY_INSUFFICIENT_DATA

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=5, seed=5010)

        legacy_problem = {
            "category": "water_depletion", "label": "Water Depletion", "field": "soil_moisture_pct",
            "status": "weak_evidence", "direction": "FALLING", "current_value": 60.0,
            "icar_value": 70.0, "icar_deviation": -10.0, "rate_per_day": -1.0, "rate_unit": "pp/day",
            "persistence_days": 3, "sourced_corroboration_notes": [], "provenance_notes": [],
            "raw_range": None,
            # no "severity" / "severity_factors" / "severity_disclaimer" keys at all
        }

        db.query(ProblemAssessmentHistory).filter(ProblemAssessmentHistory.simulation_run_id == run.id).delete()
        db.add(
            ProblemAssessmentHistory(
                simulation_run_id=run.id, day=5, crop="tomato",
                problems_json=json.dumps([legacy_problem]),
            )
        )
        db.commit()

        result = get_stored_assessment(db, run.id, day=5)
        assert result is not None
        water = result.problems[0]
        assert water.severity == SEVERITY_INSUFFICIENT_DATA
        assert water.severity_factors is None
        assert "LEGACY FORMAT" in water.severity_disclaimer
        assert "never computed" in water.severity_disclaimer
    finally:
        db.close()


def test_legacy_format_row_without_abnormal_duration_reads_without_crashing_and_is_flagged():
    """
    Backward compatibility: a problem_assessment_history row persisted
    before the abnormal_state_duration feature existed had no
    "abnormal_state_duration" key in its problems_json. get_stored_assessment
    must still read it (not crash) and must say plainly the field was
    never computed -- never silently present a day count that was never
    actually derived, and never silently drop persistence_days (which
    predates this feature and must still round-trip normally).
    """
    import json

    from app.services.stress_assessment.abnormal_duration import TIER_ICAR_SIGN_TREND_PROXY

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=5, seed=5011)

        legacy_problem = {
            "category": "water_depletion", "label": "Water Depletion", "field": "soil_moisture_pct",
            "status": "weak_evidence", "direction": "FALLING", "current_value": 60.0,
            "icar_value": 70.0, "icar_deviation": -10.0, "rate_per_day": -1.0, "rate_unit": "pp/day",
            "persistence_days": 3, "sourced_corroboration_notes": [], "provenance_notes": [],
            "raw_range": None,
            "severity": "MODERATE",
            "severity_factors": {
                "deviation_ratio": 0.14, "deviation_score": 1, "intensity_ratio": 2.5, "intensity_score": 1,
                "duration_fraction": 0.4, "duration_score": 1, "total_score": 3,
            },
            "severity_disclaimer": "irrelevant for this test",
            # no "abnormal_state_duration" key at all -- pre-feature row
        }

        db.query(ProblemAssessmentHistory).filter(ProblemAssessmentHistory.simulation_run_id == run.id).delete()
        db.add(
            ProblemAssessmentHistory(
                simulation_run_id=run.id, day=5, crop="tomato",
                problems_json=json.dumps([legacy_problem]),
            )
        )
        db.commit()

        result = get_stored_assessment(db, run.id, day=5)
        assert result is not None
        water = result.problems[0]
        assert water.persistence_days == 3  # pre-existing field, unaffected
        assert water.severity == "MODERATE"  # pre-existing field, unaffected
        assert water.abnormal_state_duration.days is None
        assert water.abnormal_state_duration.tier == TIER_ICAR_SIGN_TREND_PROXY
        assert "LEGACY FORMAT" in water.abnormal_state_duration.provenance_note
        assert "never computed" in water.abnormal_state_duration.provenance_note
    finally:
        db.close()


def test_history_module_never_touches_phase2_generation_files():
    code = inspect.getsource(history_module).split('"""', 2)[-1]
    assert "app.routes.simulator" not in code
    assert "app.simulator_cli" not in code
    assert "def create_run(" not in code
    assert "def generate(" not in code
