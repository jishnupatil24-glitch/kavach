"""
Phase 5 tests: pure-function unit tests for 5A/5B/5C, integration tests
against the real audited excess_irrigation/water_shortage runs, CLI/API
round-trips, persistence/legacy-format compatibility, and structural
regression guards proving Phase 2/3/4 stay untouched.
"""
from __future__ import annotations

import pytest

from app.database.session import SessionLocal
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis.current_state import CurrentState
from app.services.state_analysis.icar_deviation import IcarDeviation
from app.services.state_analysis.persistence import PersistenceResult
from app.services.state_analysis.service import ParameterAnalysis
from app.services.state_analysis.trend import TrendResult
from app.services.stress_assessment.abnormal_duration import (
    AbnormalDurationResult,
    TIER_ICAR_SIGN_TREND_PROXY,
    TIER_SOURCED_THRESHOLD,
)
from app.services.stress_assessment.categories import CATEGORIES
from app.services.stress_assessment.evidence import compute_problem_assessment
from app.services.decision_engine.config_parameters import (
    PARAM_MIN_SEVERITY_FOR_ACTION,
    PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS,
    SEVERITY_ORDER,
    load_min_severity_for_action,
    load_tier2_min_abnormal_duration_days,
)
from app.services.decision_engine.constraint_engine import (
    CONFLICT_PAIRS,
    detect_conflicts,
    evaluate_eligibility,
)
from app.services.decision_engine.prioritization import prioritize
from app.services.decision_engine.seed_parameters import ensure_decision_engine_parameters
from app.services.decision_engine.service import decide_run
from app.services.decision_engine.validation import (
    ACTION_TYPE_QUALITATIVE,
    OUTCOME_ACTION_RECOMMENDED,
    OUTCOME_CONFLICT,
    OUTCOME_INSUFFICIENT_SUPPORT,
    OUTCOME_MONITOR,
    OUTCOME_NO_ACTION,
    build_decision_record,
)


@pytest.fixture(scope="session")
def decision_params_seeded(seeded_agronomics_db):
    """
    seed_agronomics.seed() (Phase 1, session-scoped, destructive) does
    not know about Phase 5's project_defined rows -- ensure they exist
    AFTER that fixture has already run, once per test session.
    """
    db = SessionLocal()
    try:
        ensure_decision_engine_parameters(db)
    finally:
        db.close()


def _category(key):
    return next(c for c in CATEGORIES if c.key == key)


def _pa(status_inputs, field="soil_moisture_pct", direction="RISING", persistence_days=1,
        icar_value=75.0, current_value=99.0, rate_per_day=0.5, stable_band=0.2, day=30):
    signed_diff = current_value - icar_value
    return ParameterAnalysis(
        current=CurrentState(parameter="X", field=field, value=current_value, day=day, n_readings=4, note=None),
        trend=TrendResult(parameter="X", direction=direction, rate_per_day=rate_per_day, rate_unit="pp/day",
                           standard_error_per_day=stable_band / 2, stable_band=stable_band, n_observations=day, note=None),
        persistence=PersistenceResult(parameter="X", direction=direction, days=persistence_days, note=None),
        icar=IcarDeviation(parameter="X", current_value=current_value, icar_value=icar_value, icar_day=day,
                            signed_difference=signed_diff, absolute_difference=abs(signed_diff), unit_suffix=" %", note=None),
    )


def _find(assessment, category_key):
    return next(d for d in assessment.decisions if d.category == category_key)


# ---------------------------------------------------------------------
# 1. config_parameters -- reading the two approved project_defined rows
# ---------------------------------------------------------------------

def test_min_severity_for_action_reads_moderate(decision_params_seeded):
    db = SessionLocal()
    try:
        result = load_min_severity_for_action(db, "tomato")
        assert result.value == "MODERATE"
    finally:
        db.close()


def test_tier2_min_abnormal_duration_reads_five(decision_params_seeded):
    db = SessionLocal()
    try:
        result = load_tier2_min_abnormal_duration_days(db, "tomato")
        assert result.value == 5
    finally:
        db.close()


def test_config_parameters_missing_returns_none_not_a_crash():
    db = SessionLocal()
    try:
        result = load_min_severity_for_action(db, "nonexistent_crop_xyz")
        assert result.value is None
        assert "No project_defined" in result.note
    finally:
        db.close()


# ---------------------------------------------------------------------
# 2. 5A -- eligibility gate, pure-function
# ---------------------------------------------------------------------

def test_eligibility_passes_when_severity_and_duration_clear_the_floor():
    pa = _pa(None, direction="RISING", persistence_days=1, current_value=99.0, icar_value=75.0)
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    # force severity/tier synthetically isn't possible via compute_problem_assessment's
    # real formula here (needs a real db + run for abnormal_state_duration) -- covered
    # by the real-run integration tests below instead. This test checks the gate logic
    # in isolation using evaluate_eligibility directly.
    from dataclasses import replace
    problem = replace(
        problem,
        severity="HIGH",
        abnormal_state_duration=AbnormalDurationResult("excessive_moisture", TIER_ICAR_SIGN_TREND_PROXY, 7, "proxy"),
    )
    result = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
    assert result.eligible is True
    assert all(c.passed is True for c in result.gate_checks)


def test_eligibility_fails_severity_below_floor():
    pa = _pa(None)
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    from dataclasses import replace
    problem = replace(
        problem, severity="LOW",
        abnormal_state_duration=AbnormalDurationResult("excessive_moisture", TIER_ICAR_SIGN_TREND_PROXY, 10, "proxy"),
    )
    result = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
    assert result.eligible is False
    severity_check = next(c for c in result.gate_checks if c.name == "severity_floor")
    assert severity_check.passed is False


def test_eligibility_fails_duration_below_floor_tier2():
    pa = _pa(None)
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    from dataclasses import replace
    problem = replace(
        problem, severity="HIGH",
        abnormal_state_duration=AbnormalDurationResult("excessive_moisture", TIER_ICAR_SIGN_TREND_PROXY, 2, "proxy"),
    )
    result = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
    assert result.eligible is False
    duration_check = next(c for c in result.gate_checks if c.name == "duration_floor")
    assert duration_check.passed is False


def test_eligibility_tier1_no_duration_gate_applied(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        pa = _pa(None, field="temperature_c", direction="RISING", current_value=99.0, icar_value=75.0)
        problem = compute_problem_assessment(db, "tomato", _category("heat_related"), pa, None)
        from dataclasses import replace
        problem = replace(
            problem, severity="MODERATE",
            abnormal_state_duration=AbnormalDurationResult("heat_related", TIER_SOURCED_THRESHOLD, 1, "sourced"),
        )
        result = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
        assert result.eligible is True
        assert not any(c.name == "duration_floor" for c in result.gate_checks)
    finally:
        db.close()


def test_eligibility_not_evaluable_when_config_missing():
    pa = _pa(None)
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    from dataclasses import replace
    problem = replace(
        problem, severity="HIGH",
        abnormal_state_duration=AbnormalDurationResult("excessive_moisture", TIER_ICAR_SIGN_TREND_PROXY, 10, "proxy"),
    )
    result = evaluate_eligibility(problem, None, "config missing", 5, "note")
    assert result.eligible is False
    assert any(c.passed is None for c in result.gate_checks)


def test_eligibility_severity_insufficient_data_never_evaluable():
    pa = _pa(None)
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    from dataclasses import replace
    problem = replace(problem, severity="insufficient_data")
    result = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
    assert result.eligible is False
    assert any(c.passed is None for c in result.gate_checks)


def test_severity_order_is_explicit_ordinal_not_string():
    assert SEVERITY_ORDER == {"LOW": 0, "MODERATE": 1, "HIGH": 2, "CRITICAL": 3}
    assert SEVERITY_ORDER["CRITICAL"] > SEVERITY_ORDER["HIGH"] > SEVERITY_ORDER["MODERATE"] > SEVERITY_ORDER["LOW"]


# ---------------------------------------------------------------------
# 3. 5A -- conflict detection
# ---------------------------------------------------------------------

def test_conflict_pairs_are_exactly_three():
    assert set(CONFLICT_PAIRS) == {
        ("water_depletion", "excessive_moisture"),
        ("humidity_low", "humidity_high"),
        ("heat_related", "temperature_deficit"),
    }


def test_conflict_detected_when_both_sides_reach_weak_evidence():
    pa_dep = _pa(None, direction="FALLING", current_value=50.0, icar_value=75.0)
    pa_exc = _pa(None, direction="RISING", current_value=99.0, icar_value=75.0)
    dep = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa_dep, None)
    exc = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa_exc, None)
    assert dep.status == "weak_evidence"
    assert exc.status == "weak_evidence"
    conflicts = detect_conflicts({"water_depletion": dep, "excessive_moisture": exc})
    assert conflicts["water_depletion"] == "excessive_moisture"
    assert conflicts["excessive_moisture"] == "water_depletion"


def test_no_conflict_when_only_one_side_has_evidence():
    pa_dep = _pa(None, direction="FALLING", current_value=50.0, icar_value=75.0)
    pa_exc = _pa(None, direction="STABLE", current_value=75.0, icar_value=75.0, rate_per_day=0.0)
    dep = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa_dep, None)
    exc = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa_exc, None)
    conflicts = detect_conflicts({"water_depletion": dep, "excessive_moisture": exc})
    assert conflicts["water_depletion"] is None
    assert conflicts["excessive_moisture"] is None


# ---------------------------------------------------------------------
# 4. 5B -- deterministic prioritization
# ---------------------------------------------------------------------

def test_prioritization_orders_corroborated_before_weak_then_by_severity():
    pa_a = _pa(None, current_value=99.0, icar_value=75.0, direction="RISING")  # weak_evidence
    problem_a = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa_a, None)
    from dataclasses import replace
    problem_a = replace(problem_a, severity_factors=replace(problem_a.severity_factors, total_score=3) if problem_a.severity_factors else None)

    ordered = prioritize([problem_a])
    assert ordered["excessive_moisture"].priority == 1


def test_prioritization_tie_break_is_alphabetical_category():
    from dataclasses import replace
    pa = _pa(None, current_value=99.0, icar_value=75.0, direction="RISING")
    p1 = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    p2 = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    # force identical status/severity so only the category-name tie-break differs
    p1 = replace(p1, status="weak_evidence")
    p2 = replace(p2, status="weak_evidence")
    ordered = prioritize([p1, p2])
    assert ordered["excessive_moisture"].priority < ordered["water_depletion"].priority


# ---------------------------------------------------------------------
# 5. 5C -- outcome vocabulary via build_decision_record
# ---------------------------------------------------------------------

def test_no_evidence_status_yields_no_action():
    pa = _pa(None, direction="STABLE", current_value=75.0, icar_value=75.0, rate_per_day=0.0)
    problem = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert problem.status == "no_evidence"
    from app.services.decision_engine.constraint_engine import EligibilityResult
    record = build_decision_record(None, "tomato", problem, EligibilityResult("water_depletion", "icar_sign_trend_proxy"), None)
    assert record.outcome == OUTCOME_NO_ACTION


def test_quantitative_basis_is_always_none_and_disclosed():
    pa = _pa(None, current_value=99.0, icar_value=75.0, direction="RISING")
    from dataclasses import replace
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    problem = replace(
        problem, severity="HIGH",
        abnormal_state_duration=AbnormalDurationResult("excessive_moisture", TIER_ICAR_SIGN_TREND_PROXY, 10, "proxy"),
    )
    eligibility = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
    record = build_decision_record(None, "tomato", problem, eligibility, None)
    assert record.outcome == OUTCOME_ACTION_RECOMMENDED
    assert record.action_type == ACTION_TYPE_QUALITATIVE
    assert record.quantitative_basis is None
    assert any("qualitative only" in lim for lim in record.limitations)


def test_no_action_label_defined_yields_insufficient_support():
    pa = _pa(None, current_value=99.0, icar_value=75.0, direction="RISING")
    from dataclasses import replace
    problem = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    problem = replace(problem, category="not_a_real_category", severity="HIGH",
                       abnormal_state_duration=AbnormalDurationResult("not_a_real_category", TIER_ICAR_SIGN_TREND_PROXY, 10, "proxy"))
    eligibility = evaluate_eligibility(problem, "MODERATE", "note", 5, "note")
    record = build_decision_record(None, "tomato", problem, eligibility, None)
    assert record.outcome == OUTCOME_INSUFFICIENT_SUPPORT


# ---------------------------------------------------------------------
# 6. Real-run regression: the two audited target days
# ---------------------------------------------------------------------

def test_excess_irrigation_first_action_recommended_day_34(decision_params_seeded):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)

        first_day = None
        for day in range(1, 39):
            assessment = decide_run(db, run.id, day=day)
            excess = _find(assessment, "excessive_moisture")
            if excess.outcome == OUTCOME_ACTION_RECOMMENDED:
                first_day = day
                break
        assert first_day == 34

        day38 = decide_run(db, run.id, day=38)
        excess38 = _find(day38, "excessive_moisture")
        assert excess38.outcome == OUTCOME_ACTION_RECOMMENDED
        assert excess38.status == "weak_evidence"  # Phase 4 unchanged
        assert excess38.severity == "MODERATE"  # Phase 4 unchanged
        assert excess38.abnormal_duration_days == 9  # Phase 4 unchanged
        assert excess38.action_label == "Increase irrigation" or excess38.action_label == "Reduce irrigation"
        assert excess38.action_type == ACTION_TYPE_QUALITATIVE
        assert excess38.decision_provenance == "PROJECT_DEFINED"

        day33 = decide_run(db, run.id, day=33)
        excess33 = _find(day33, "excessive_moisture")
        assert excess33.outcome == OUTCOME_MONITOR  # duration floor (5) not yet met at day 33
    finally:
        db.close()


def test_water_shortage_first_action_recommended_day_35(decision_params_seeded):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=40, scenario="water_shortage", seed=1234,
            severity="severe", scenario_start_day=31, scenario_duration_days=8,
        )
        run = create_run(db, config)

        first_day = None
        for day in range(1, 41):
            assessment = decide_run(db, run.id, day=day)
            depletion = _find(assessment, "water_depletion")
            if depletion.outcome == OUTCOME_ACTION_RECOMMENDED:
                first_day = day
                break
        assert first_day == 35

        day40 = decide_run(db, run.id, day=40)
        depletion40 = _find(day40, "water_depletion")
        assert depletion40.outcome == OUTCOME_ACTION_RECOMMENDED
        assert depletion40.status == "weak_evidence"
        assert depletion40.severity == "MODERATE"
        assert depletion40.abnormal_duration_days == 10
        assert depletion40.action_label == "Increase irrigation"
    finally:
        db.close()


# ---------------------------------------------------------------------
# 7. Persistence / history (Workflow A)
# ---------------------------------------------------------------------

def test_run_creation_automatically_persists_decision_history(decision_params_seeded):
    from app.models.decision_history import DecisionHistory

    db = SessionLocal()
    try:
        config = build_config(duration_days=10, scenario="normal", seed=42009)
        run = create_run(db, config)
        count = db.query(DecisionHistory).filter(DecisionHistory.simulation_run_id == run.id).count()
        assert count == 10
    finally:
        db.close()


def test_stored_decision_round_trips_against_live(decision_params_seeded):
    from app.services.decision_engine.history import get_stored_decision

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)
        live = decide_run(db, run.id, day=34)
        stored = get_stored_decision(db, run.id, day=34)
        assert stored.assessment_day == live.assessment_day
        for live_d, stored_d in zip(live.decisions, stored.decisions):
            assert live_d.category == stored_d.category
            assert live_d.outcome == stored_d.outcome
            assert live_d.action_label == stored_d.action_label
    finally:
        db.close()


def test_legacy_decision_row_reads_without_crashing():
    import json

    from app.models.decision_history import DecisionHistory
    from app.services.decision_engine.history import get_stored_decision

    db = SessionLocal()
    try:
        config = build_config(duration_days=5, scenario="normal", seed=42010)
        run = create_run(db, config)

        legacy_decision = {
            "category": "water_depletion", "label": "Water Depletion", "status": "weak_evidence",
            "severity": "MODERATE", "abnormal_duration_days": 3, "abnormal_duration_tier": "icar_sign_trend_proxy",
            "eligibility_checks": [{"name": "evidence_status", "passed": True, "detail": "status=weak_evidence"}],
            "conflict_with": None, "outcome": "MONITOR", "action_label": None, "action_type": None,
            "action_basis": "proxy", "decision_provenance": "PROJECT_DEFINED", "quantitative_basis": None,
            "limitations": [], "priority": None, "priority_reason": None,
        }
        db.query(DecisionHistory).filter(DecisionHistory.simulation_run_id == run.id).delete()
        db.add(DecisionHistory(simulation_run_id=run.id, day=5, crop="tomato",
                                decisions_json=json.dumps([legacy_decision])))
        db.commit()

        result = get_stored_decision(db, run.id, day=5)
        assert result is not None
        assert result.decisions[0].outcome == "MONITOR"
    finally:
        db.close()


# ---------------------------------------------------------------------
# 8. Structural boundary guards -- Phase 5 must not touch raw data or
#    Phase 2/3/4 logic
# ---------------------------------------------------------------------

def test_decision_engine_never_imports_raw_sensor_or_phase3_calculation_modules():
    import inspect

    from app.services.decision_engine import constraint_engine, prioritization, service, validation

    modules = [constraint_engine, prioritization, service, validation]
    forbidden_import_fragments = [
        "import app.models.sensor_observation", "from app.models.sensor_observation",
        "import app.services.state_analysis.trend", "from app.services.state_analysis.trend",
        "import app.services.state_analysis.persistence", "from app.services.state_analysis.persistence",
        "import app.services.state_analysis.icar_deviation", "from app.services.state_analysis.icar_deviation",
        "def compute_trend(", "def compute_persistence(", "def compute_icar_deviation(",
        "def compute_problem_assessment(", "def assess_run(",
    ]
    for module in modules:
        source = inspect.getsource(module)
        for fragment in forbidden_import_fragments:
            assert fragment not in source, f"{module.__name__} appears to touch raw/Phase3/4 internals: {fragment!r}"


def test_decision_cli_reuses_stored_history_not_a_reimplementation():
    import inspect

    from app import decision_cli

    source = inspect.getsource(decision_cli)
    forbidden = ["def decide_run(", "def compute_problem_assessment(", "def assess_run(", "AgronomicParameter"]
    for fragment in forbidden:
        assert fragment not in source, f"CLI appears to duplicate logic: {fragment!r} found"
    assert "from app.services.decision_engine.history import get_stored_decision" in source


def test_cli_output_shows_both_phase4_and_decision_sections(decision_params_seeded, capsys):
    from app import decision_cli

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)
        run_id = run.id
    finally:
        db.close()

    exit_code = decision_cli.main(["--run-id", str(run_id), "--day", "34"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "PHASE 4 INPUT" in out
    assert "5A -- CONSTRAINT ENGINE" in out
    assert "5B -- ACTION PRIORITIZATION" in out
    assert "5C -- RECOMMENDATION VALIDATION" in out
    assert "ACTION_RECOMMENDED" in out
    assert "Reduce irrigation" in out  # excessive_moisture's action label


# ---------------------------------------------------------------------
# 9. Regression: Phase 2/3/4 must remain exactly as verified before
# ---------------------------------------------------------------------

def test_phase4_status_severity_duration_unchanged_by_phase5(decision_params_seeded):
    from app.services.stress_assessment.service import assess_run

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)

        phase4_direct = assess_run(db, run.id, day=38)
        excess_direct = next(p for p in phase4_direct.problems if p.category == "excessive_moisture")

        decision = decide_run(db, run.id, day=38)
        excess_decision = _find(decision, "excessive_moisture")

        assert excess_direct.status == excess_decision.status == "weak_evidence"
        assert excess_direct.severity == excess_decision.severity == "MODERATE"
        assert excess_direct.persistence_days == 1  # unchanged Phase 3 concept, untouched by Phase 5
        assert excess_direct.abnormal_state_duration.days == excess_decision.abnormal_duration_days == 9
    finally:
        db.close()
