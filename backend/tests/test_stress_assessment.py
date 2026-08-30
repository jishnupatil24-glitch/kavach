"""
Phase 4 tests: pure-function gate/evidence tests, integration tests
against real generated (and automatically Phase 3+4-persisted) runs,
API tests, and structural guards that Phase 4 stays a
detection/assessment layer -- no recommendation, no optimization, no
Constraint Engine, no duplicated Phase 3 math in the CLI.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from app.database.session import SessionLocal
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis.crop_stage_context import StageMatch
from app.services.state_analysis.current_state import CurrentState
from app.services.state_analysis.icar_deviation import IcarDeviation
from app.services.state_analysis.persistence import PersistenceResult
from app.services.state_analysis.service import InvalidDayError, ParameterAnalysis, RunNotFoundError
from app.services.state_analysis.trend import TrendResult
from app.services.stress_assessment import categories as categories_module
from app.services.stress_assessment import evidence as evidence_module
from app.services.stress_assessment import history as history_module
from app.services.stress_assessment import service as service_module
from app.services.stress_assessment.categories import CATEGORIES
from app.services.stress_assessment.evidence import (
    STATUS_CORROBORATED_EVIDENCE,
    STATUS_INSUFFICIENT_DATA,
    STATUS_NO_EVIDENCE,
    STATUS_WEAK_EVIDENCE,
    compute_problem_assessment,
    compute_raw_range,
)
from app.services.stress_assessment.service import assess_run


def _make_run(db, duration_days=40, scenario="normal", seed=1, **kwargs):
    config = build_config(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
    return create_run(db, config)


def _category(key):
    return next(c for c in CATEGORIES if c.key == key)


def _pa(direction, persistence_days, signed_diff, value=50.0, field="soil_moisture_pct"):
    return ParameterAnalysis(
        current=CurrentState(parameter="X", field=field, value=value, day=10, n_readings=4, note=None),
        trend=TrendResult(
            parameter="X", direction=direction, rate_per_day=-1.0 if direction == "FALLING" else 1.0,
            rate_unit="pp/day", standard_error_per_day=0.1, stable_band=0.2, n_observations=10, note=None,
        ),
        persistence=PersistenceResult(parameter="X", direction=direction, days=persistence_days, note=None),
        icar=IcarDeviation(
            parameter="X", current_value=value, icar_value=value - signed_diff, icar_day=10,
            signed_difference=signed_diff, absolute_difference=abs(signed_diff), unit_suffix=" %", note=None,
        ),
    )


# ---------------------------------------------------------------------
# 1. Categories
# ---------------------------------------------------------------------

def test_exactly_ten_categories_with_unique_keys():
    assert len(CATEGORIES) == 10
    assert len({c.key for c in CATEGORIES}) == 10


def test_no_excess_nutrient_or_excess_light_category_exists():
    keys = {c.key for c in CATEGORIES}
    assert "excess_light" not in keys
    assert not any("excess" in k and "nitrogen" in k for k in keys)
    assert not any("excess" in k and "phosphorus" in k for k in keys)
    assert not any("excess" in k and "potassium" in k for k in keys)


# ---------------------------------------------------------------------
# 2. Gate logic (pure, synthetic ParameterAnalysis, no DB)
# ---------------------------------------------------------------------

def test_undetermined_trend_is_insufficient_data():
    pa = _pa("UNDETERMINED", None, -5.0)
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert result.status == STATUS_INSUFFICIENT_DATA


def test_wrong_direction_is_no_evidence():
    # water_depletion wants FALLING; RISING never qualifies regardless of other signals
    pa = _pa("RISING", 5, -5.0)
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert result.status == STATUS_NO_EVIDENCE


def test_no_persistence_is_no_evidence():
    pa = _pa("FALLING", None, -5.0)
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert result.status == STATUS_NO_EVIDENCE


def test_wrong_icar_deviation_sign_is_no_evidence():
    # FALLING + persistence exists, but current is ABOVE ICAR (positive), not below
    pa = _pa("FALLING", 5, +5.0)
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert result.status == STATUS_NO_EVIDENCE


def test_full_gate_with_no_sourced_threshold_is_weak_evidence():
    pa = _pa("FALLING", 5, -10.0)
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert result.status == STATUS_WEAK_EVIDENCE
    assert result.sourced_corroboration_notes == []
    assert len(result.provenance_notes) == 1
    assert "context_dependent" in result.provenance_notes[0]


def test_full_gate_with_matched_corroboration_is_corroborated_evidence(seeded_agronomics_db):
    db = SessionLocal()
    try:
        pa = _pa("RISING", 5, +8.0, value=38.0, field="temperature_c")
        result = compute_problem_assessment(db, "tomato", _category("heat_related"), pa, None)
        assert result.status == STATUS_CORROBORATED_EVIDENCE
        assert len(result.sourced_corroboration_notes) == 1
        assert "No cultivar is configured" in result.sourced_corroboration_notes[0]
        assert "30.0" in result.sourced_corroboration_notes[0] or "30" in result.sourced_corroboration_notes[0]
    finally:
        db.close()


def test_full_gate_with_unmatched_corroboration_is_weak_evidence(seeded_agronomics_db):
    db = SessionLocal()
    try:
        # 20C is below all 4 sourced critical-stress values (25/30/32/45) -- gate met but not corroborated
        pa = _pa("RISING", 5, +2.0, value=20.0, field="temperature_c")
        result = compute_problem_assessment(db, "tomato", _category("heat_related"), pa, None)
        assert result.status == STATUS_WEAK_EVIDENCE
        # the provenance note (all 4 cultivar values) is still shown even when not matched
        assert len(result.sourced_corroboration_notes) == 1
    finally:
        db.close()


def test_humidity_low_three_zone_boundary(seeded_agronomics_db):
    # humidity_min_pct sourced range is 30-50% (30 = failure floor, 50 = optimal-band
    # start, per Shamshiri et al. 2018's own notes -- two distinct calibration points,
    # not one disputed number). Corrected 3-zone behavior, approved:
    #   at/above 50%  -> NO_EVIDENCE
    #   30% - 50%     -> WEAK_EVIDENCE, scaled by boundary_ratio
    #   at/below 30%  -> CORROBORATED_EVIDENCE
    db = SessionLocal()
    try:
        # at the optimal edge exactly -> not abnormal at all
        pa_edge = _pa("FALLING", 3, -5.0, value=50.0, field="humidity_pct")
        result_edge = compute_problem_assessment(db, "tomato", _category("humidity_low"), pa_edge, None)
        assert result_edge.status == STATUS_NO_EVIDENCE

        # mid sub-optimal zone -> weak evidence, boundary_ratio = (50-45)/20 = 0.25
        pa_mid = _pa("FALLING", 3, -5.0, value=45.0, field="humidity_pct")
        result_mid = compute_problem_assessment(db, "tomato", _category("humidity_low"), pa_mid, None)
        assert result_mid.status == STATUS_WEAK_EVIDENCE
        assert result_mid.severity_factors.deviation_ratio == pytest.approx(0.25)
        assert "boundary_ratio=0.25" in result_mid.sourced_corroboration_notes[0]

        # at/below the failure floor -> corroborated
        pa_floor = _pa("FALLING", 3, -5.0, value=25.0, field="humidity_pct")
        result_floor = compute_problem_assessment(db, "tomato", _category("humidity_low"), pa_floor, None)
        assert result_floor.status == STATUS_CORROBORATED_EVIDENCE
        assert result_floor.severity_factors.deviation_ratio == pytest.approx(1.0)

        # far above the band entirely -> no evidence (real bug shape: was previously
        # weak_evidence at 70% against a 50% boundary)
        pa_far = _pa("FALLING", 3, -5.0, value=70.0, field="humidity_pct")
        result_far = compute_problem_assessment(db, "tomato", _category("humidity_low"), pa_far, None)
        assert result_far.status == STATUS_NO_EVIDENCE
        assert "not crossed" in result_far.sourced_corroboration_notes[0]
    finally:
        db.close()


def test_humidity_high_three_zone_boundary(seeded_agronomics_db):
    # humidity_max_pct sourced range is 80-100% (80 = onset edge, 100 = physical
    # ceiling). No existing run/scenario in this repo ever reaches this band (max
    # observed humidity across all stored data is ~76.79%), so this is the first
    # coverage of humidity_high's corroboration at all -- synthetic values required.
    db = SessionLocal()
    try:
        pa_edge = _pa("RISING", 3, 5.0, value=80.0, field="humidity_pct")
        result_edge = compute_problem_assessment(db, "tomato", _category("humidity_high"), pa_edge, None)
        assert result_edge.status == STATUS_NO_EVIDENCE

        pa_mid = _pa("RISING", 3, 5.0, value=90.0, field="humidity_pct")
        result_mid = compute_problem_assessment(db, "tomato", _category("humidity_high"), pa_mid, None)
        assert result_mid.status == STATUS_WEAK_EVIDENCE
        assert result_mid.severity_factors.deviation_ratio == pytest.approx(0.5)
        assert "boundary_ratio=0.50" in result_mid.sourced_corroboration_notes[0]

        pa_ceiling = _pa("RISING", 3, 5.0, value=100.0, field="humidity_pct")
        result_ceiling = compute_problem_assessment(db, "tomato", _category("humidity_high"), pa_ceiling, None)
        assert result_ceiling.status == STATUS_CORROBORATED_EVIDENCE
        assert result_ceiling.severity_factors.deviation_ratio == pytest.approx(1.0)

        pa_below = _pa("RISING", 3, 5.0, value=75.0, field="humidity_pct")
        result_below = compute_problem_assessment(db, "tomato", _category("humidity_high"), pa_below, None)
        assert result_below.status == STATUS_NO_EVIDENCE
    finally:
        db.close()


def test_humidity_generic_proxy_cannot_create_evidence_without_boundary_crossing(seeded_agronomics_db):
    """
    Regression test for the confirmed bug: the generic trend/persistence/
    ICAR-sign proxy (adverse_trend_matched + persistence_exists +
    icar_deviation_adverse) must NOT be able to produce humidity evidence
    when the sourced boundary was never crossed -- even when all three
    generic conditions are individually satisfied.
    """
    db = SessionLocal()
    try:
        # humidity_low: FALLING + persistence + negative ICAR deviation all match
        # the generic gate perfectly, but 73.63% never crosses the 50% boundary --
        # this is the exact real run_id=1/day=3 shape that produced the bug.
        pa_low = _pa("FALLING", 3, -0.37, value=73.63, field="humidity_pct")
        result_low = compute_problem_assessment(db, "tomato", _category("humidity_low"), pa_low, None)
        assert result_low.status == STATUS_NO_EVIDENCE

        # humidity_high: RISING + persistence + positive ICAR deviation all match
        # the generic gate, but 75% never crosses the 80% boundary.
        pa_high = _pa("RISING", 3, 5.0, value=75.0, field="humidity_pct")
        result_high = compute_problem_assessment(db, "tomato", _category("humidity_high"), pa_high, None)
        assert result_high.status == STATUS_NO_EVIDENCE
    finally:
        db.close()


# ---------------------------------------------------------------------
# 3. Raw 6-hour range (descriptive only)
# ---------------------------------------------------------------------

def _obs(**fields):
    base = dict(temperature_c=None, humidity_pct=None, soil_moisture_pct=None,
                daily_dli_mol_m2_day=None, soil_n_mg_kg=None, soil_p_mg_kg=None, soil_k_mg_kg=None)
    base.update(fields)
    return SimpleNamespace(**base)


def test_raw_range_min_max_and_label():
    observations = [_obs(temperature_c=v) for v in (20.0, 25.0, 22.0, 18.0)]
    r = compute_raw_range(observations, "temperature_c")
    assert r.min_value == 18.0
    assert r.max_value == 25.0
    assert r.n_readings == 4
    assert "not used as an independent stress signal" in r.label


def test_raw_range_none_when_no_data():
    observations = [_obs(temperature_c=20.0)]  # soil_moisture_pct never set
    assert compute_raw_range(observations, "soil_moisture_pct") is None


def test_raw_range_never_influences_the_gate():
    """The gate must not change status merely because a raw_range is attached or not."""
    pa = _pa("FALLING", 5, -10.0)
    without_range = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    with_range = compute_problem_assessment(
        None, "tomato", _category("water_depletion"), pa,
        compute_raw_range([_obs(soil_moisture_pct=v) for v in (60, 58, 55, 52)], "soil_moisture_pct"),
    )
    assert without_range.status == with_range.status == STATUS_WEAK_EVIDENCE


# ---------------------------------------------------------------------
# 4. Integration: real generated + automatically persisted runs
# ---------------------------------------------------------------------

def test_assess_run_returns_all_ten_categories(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=30, seed=42001)  # create_run auto-persists Phase 3 AND Phase 4
        result = assess_run(db, run.id)
        assert len(result.problems) == 10
        assert {p.category for p in result.problems} == {c.key for c in CATEGORIES}
    finally:
        db.close()


def test_assess_run_day_one_is_insufficient_data_for_every_category(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=42002)
        result = assess_run(db, run.id, day=1)
        for p in result.problems:
            assert p.status == STATUS_INSUFFICIENT_DATA
    finally:
        db.close()


def test_assess_run_severe_water_shortage_reaches_weak_evidence_for_water_depletion(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        run = _make_run(
            db, duration_days=40, scenario="water_shortage", seed=42003,
            severity="severe", scenario_start_day=5, scenario_duration_days=30,
        )
        result = assess_run(db, run.id, day=25)
        water = next(p for p in result.problems if p.category == "water_depletion")
        assert water.status in (STATUS_WEAK_EVIDENCE, STATUS_CORROBORATED_EVIDENCE)
        assert water.direction == "FALLING"
        assert water.icar_deviation is not None and water.icar_deviation < 0
        assert water.persistence_days is not None
    finally:
        db.close()


def test_assess_run_severe_heatwave_reaches_evidence_for_heat_related(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        run = _make_run(
            db, duration_days=40, scenario="heatwave", seed=42004,
            severity="severe", scenario_start_day=5, scenario_duration_days=30,
        )
        result = assess_run(db, run.id, day=25)
        heat = next(p for p in result.problems if p.category == "heat_related")
        assert heat.status in (STATUS_WEAK_EVIDENCE, STATUS_CORROBORATED_EVIDENCE)
        assert heat.direction == "RISING"
    finally:
        db.close()


def test_assess_run_isolates_multiple_runs(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        run_a = _make_run(db, duration_days=15, scenario="heatwave", seed=42005,
                           severity="severe", scenario_start_day=2, scenario_duration_days=10)
        run_b = _make_run(db, duration_days=15, seed=42006)  # normal
        result_a = assess_run(db, run_a.id)
        result_b = assess_run(db, run_b.id)
        assert result_a.run_id == run_a.id
        assert result_b.run_id == run_b.id
    finally:
        db.close()


def test_assess_run_invalid_run_id_raises(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        # nonexistent run -> Phase 3's get_stored_analysis raises RunNotFoundError first
        with pytest.raises(RunNotFoundError):
            assess_run(db, 9_999_999)
    finally:
        db.close()


def test_assess_run_raises_when_phase3_history_absent(seeded_db, seeded_agronomics_db):
    from app.models.state_analysis_history import StateAnalysisHistory

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=42007)
        db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).delete()
        db.commit()
        with pytest.raises(InvalidDayError):
            assess_run(db, run.id)
    finally:
        db.close()


def test_evidenced_problems_filters_correctly(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=42008)
        result = assess_run(db, run.id, day=1)  # everything insufficient_data on day 1
        assert result.evidenced_problems() == []
    finally:
        db.close()


# ---------------------------------------------------------------------
# 5. API
# ---------------------------------------------------------------------

def test_api_stress_assessment_returns_full_structure(api_client):
    create_resp = api_client.post("/api/simulator/runs", json={"duration_days": 20, "scenario": "normal", "seed": 900})
    run_id = create_resp.json()["id"]
    resp = api_client.get(f"/api/assessment/tomato/runs/{run_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["problems"]) == 10
    assert body["run_id"] == run_id


def test_api_stress_assessment_404_for_nonexistent_run(api_client):
    resp = api_client.get("/api/assessment/tomato/runs/9999999")
    assert resp.status_code == 404


def test_api_and_cli_history_agree(seeded_db, seeded_agronomics_db, api_client):
    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=20, seed=901)
        run_id = run.id
    finally:
        db.close()

    from app.services.stress_assessment.history import get_stored_assessment

    db2 = SessionLocal()
    try:
        stored = get_stored_assessment(db2, run_id)
    finally:
        db2.close()

    api_body = api_client.get(f"/api/assessment/tomato/runs/{run_id}").json()
    assert api_body["assessment_day"] == stored.assessment_day
    api_water = next(p for p in api_body["problems"] if p["category"] == "water_depletion")
    stored_water = next(p for p in stored.problems if p.category == "water_depletion")
    assert api_water["direction"] == stored_water.direction


# ---------------------------------------------------------------------
# 6. Structural guards
# ---------------------------------------------------------------------

def test_no_recommendation_or_optimization_vocabulary_anywhere_in_phase4():
    from app import stress_assessment_cli

    modules = [categories_module, evidence_module, service_module, history_module, stress_assessment_cli]
    forbidden_words = [
        "irrigate", "fertiliz", "pump", "recommend", "optimi", "constraint engine",
        "actuator", "valid action", "reinforcement", "neural", "llm",
    ]
    for module in modules:
        source = inspect.getsource(module).lower()
        for word in forbidden_words:
            assert word not in source, f"{module.__name__} contains forbidden vocabulary: {word!r}"


def test_stress_assessment_package_never_imports_simulator_internals():
    modules = [categories_module, evidence_module, service_module, history_module]
    forbidden = [
        "simulator.generator", "simulator.causal_model", "simulator.calibration",
        "simulator.scenarios", "simulator.rng", "simulator.constants",
        "simulation_internal_state",
    ]
    for module in modules:
        source = inspect.getsource(module)
        for fragment in forbidden:
            assert fragment not in source, f"{module.__name__} references {fragment!r}"


def test_stress_assessment_service_never_recomputes_phase3_math():
    """Phase 4's service must consume Phase 3's read path, never analyze_run
    (which would mean recomputing trend/rate/persistence/ICAR itself)."""
    code = inspect.getsource(service_module).split('"""', 2)[-1]  # skip the module docstring
    assert "analyze_run" not in code
    assert "def compute_trend(" not in code
    assert "def compute_persistence(" not in code
    assert "def compute_icar_deviation(" not in code
    assert "from app.services.state_analysis.history import get_stored_analysis" in code


def test_no_optimizer_or_llm_module_exists():
    """
    Phase 5 (app.services.decision_engine, including
    constraint_engine.py) is now explicitly approved and implemented --
    "constraint_engine"/"decision_engine" were removed from this guard
    for that reason. What remains forbidden is still true: no
    mathematical/multi-objective optimizer and no LLM anywhere in the
    decision path -- 5B is deterministic prioritization (not
    optimization) and 5C is deterministic validation (not an LLM
    judgment), per the approved Phase 5 design.
    """
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[1] / "app"
    forbidden_fragments = ["optimizer", "llm", "gemini"]
    offending = [
        str(p) for p in app_dir.rglob("*.py")
        if any(fragment in p.stem.lower() for fragment in forbidden_fragments)
    ]
    assert offending == []
