"""
Phase 3 tests: pure-function unit tests for trend/rate/persistence/ICAR
math, integration tests against a real generated simulation, API tests,
and structural guards that Phase 3 stays a state-analysis layer (no
diagnosis/recommendation logic, no simulator-internal coupling).
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest

from app.services.simulator.baseline import BaselineDay
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis import crop_stage_context, icar_deviation, persistence, service, trend
from app.services.state_analysis.crop_stage_context import resolve_agronomic_context, resolve_crop_stages
from app.services.state_analysis.icar_deviation import compute_icar_deviation
from app.services.state_analysis.persistence import compute_persistence
from app.services.state_analysis.service import (
    InvalidDayError,
    RunNotFoundError,
    _data_quality_notes,
    analyze_run,
)
from app.services.state_analysis.trend import MIN_OBSERVATIONS_FOR_TREND, compute_trend


# ---------------------------------------------------------------------
# 1. Trend (pure function, synthetic data)
# ---------------------------------------------------------------------

def test_trend_undetermined_with_fewer_than_minimum_observations():
    points = [(0.0, 10.0), (1.0, 11.0)]
    result = compute_trend("Temperature", points, "°C/day")
    assert result.direction == "UNDETERMINED"
    assert result.rate_per_day is None
    assert "at least" in result.note


def test_trend_rising_with_clear_linear_signal_and_zero_noise():
    points = [(float(i), 10.0 + i) for i in range(5)]  # slope exactly 1.0/day
    result = compute_trend("Temperature", points, "°C/day")
    assert result.direction == "RISING"
    assert result.rate_per_day == pytest.approx(1.0)
    assert result.n_observations == 5


def test_trend_falling_with_clear_linear_signal():
    points = [(float(i), 100.0 - 2.0 * i) for i in range(6)]
    result = compute_trend("Soil Moisture", points, "pp/day")
    assert result.direction == "FALLING"
    assert result.rate_per_day == pytest.approx(-2.0)


def test_trend_stable_when_slope_is_within_noise_derived_band():
    # Small, evenly-alternating jitter around a flat mean -- no real
    # linear signal, so the slope should fall inside the residual-noise
    # stable band.
    values = [50.0, 50.4, 49.7, 50.3, 49.8, 50.2, 49.9, 50.1]
    points = [(float(i), v) for i, v in enumerate(values)]
    result = compute_trend("Humidity", points, "%/day")
    assert result.direction == "STABLE"
    assert result.stable_band is not None


def test_trend_degenerate_same_elapsed_time_is_undetermined():
    points = [(5.0, 10.0), (5.0, 12.0), (5.0, 11.0)]
    result = compute_trend("Temperature", points, "°C/day")
    assert result.direction == "UNDETERMINED"
    assert "same elapsed time" in result.note


def test_min_observations_constant_is_three():
    # Regression maths needs n-2 >= 1 degrees of freedom; documented here
    # so a future change to this constant is a deliberate, visible edit.
    assert MIN_OBSERVATIONS_FOR_TREND == 3


# ---------------------------------------------------------------------
# 2. Persistence (pure function, synthetic data)
# ---------------------------------------------------------------------

def test_persistence_counts_consecutive_falling_days():
    # Day 31..35 falling, mirrors the worked example from the Phase 3 spec.
    points = []
    for day, value in zip(range(31, 36), [72, 69, 65, 61, 57]):
        for hour in (0, 6, 12, 18):
            points.append((day, float(value)))
    # derive a real stable_band from a matching trend computation
    trend_points = [(day + h / 24.0, v) for (day, v), h in zip(points, [0, 6, 12, 18] * 5)]
    t = compute_trend("Soil Moisture", trend_points, "pp/day")
    assert t.direction == "FALLING"
    result = compute_persistence("Soil Moisture", points, t.direction, t.stable_band)
    assert result.direction == "FALLING"
    assert result.days == 5


def test_persistence_undetermined_with_fewer_than_two_days():
    points = [(1, 50.0), (1, 51.0), (1, 49.0), (1, 50.5)]
    result = compute_persistence("Temperature", points, "STABLE", 0.5)
    assert result.days is None
    assert "at least 2" in result.note


def test_persistence_undetermined_when_trend_undetermined():
    result = compute_persistence("Temperature", [(1, 50.0), (2, 51.0)], "UNDETERMINED", None)
    assert result.days is None
    assert "undetermined" in result.note.lower()


# ---------------------------------------------------------------------
# 3. ICAR deviation (pure function, synthetic baseline)
# ---------------------------------------------------------------------

def _fake_baseline_day(day: int, moisture: float) -> BaselineDay:
    return BaselineDay(
        day=day, temperature_c=25.0, humidity_pct=60.0, soil_moisture_pct=moisture,
        dli_mol_m2_day=18.0, soil_n_mg_kg=150.0, soil_p_mg_kg=30.0, soil_k_mg_kg=300.0,
    )


def test_icar_deviation_signed_and_absolute():
    baseline = {35: _fake_baseline_day(35, 60.0)}
    result = compute_icar_deviation("Soil Moisture", 57.0, 35, "soil_moisture_pct", baseline, " %")
    assert result.icar_value == 60.0
    assert result.signed_difference == pytest.approx(-3.0)
    assert result.absolute_difference == pytest.approx(3.0)


def test_icar_deviation_unavailable_outside_reference_range():
    baseline = {35: _fake_baseline_day(35, 60.0)}
    result = compute_icar_deviation("Soil Moisture", 57.0, 200, "soil_moisture_pct", baseline, " %")
    assert result.icar_value is None
    assert result.signed_difference is None
    assert "1-120" in result.note


# ---------------------------------------------------------------------
# 4. Crop-stage resolution incl. Day 100 overlap, and agronomic context
# ---------------------------------------------------------------------

def test_day_100_matches_both_overlapping_kc_stages(seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        matches = resolve_crop_stages(db, "tomato", 100)
        names = {m.name for m in matches}
        assert "kc_mid_stage" in names
        assert "kc_late_stage" in names
        assert "full_cycle" in names
    finally:
        db.close()


def test_day_50_matches_only_one_kc_stage_plus_full_cycle(seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        matches = resolve_crop_stages(db, "tomato", 50)
        names = {m.name for m in matches}
        assert names == {"full_cycle", "kc_development_stage"}
    finally:
        db.close()


def test_daf_qld_day_less_stages_never_matched_by_day(seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        for day in (1, 30, 60, 90, 120):
            matches = resolve_crop_stages(db, "tomato", day)
            names = {m.name for m in matches}
            assert "germination" not in names
            assert "early_vegetative_growth" not in names
            assert "flowering_fruit_set" not in names
            assert "fruit_growth" not in names
    finally:
        db.close()


def test_agronomic_context_returns_all_kc_context_variants(seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        matches = resolve_crop_stages(db, "tomato", 70)  # kc_mid_stage
        kc_mid_id = next(m.stage_id for m in matches if m.name == "kc_mid_stage")
        items = resolve_agronomic_context(db, "tomato", [kc_mid_id])
        kc_mid_items = [i for i in items if i.parameter_name == "kc_mid"]
        assert len(kc_mid_items) == 3
        assert all(i.status == "sourced" for i in kc_mid_items)
    finally:
        db.close()


def test_agronomic_context_empty_for_no_stage_ids():
    assert resolve_agronomic_context(None, "tomato", []) == []


# ---------------------------------------------------------------------
# 5. Data-quality notes (pure function, synthetic observation-like objects)
# ---------------------------------------------------------------------

def _obs(day, hour, humidity_pct=50.0, soil_moisture_pct=50.0):
    return SimpleNamespace(day=day, hour=hour, humidity_pct=humidity_pct, soil_moisture_pct=soil_moisture_pct)


def test_data_quality_flags_missing_day():
    observations = [_obs(1, h) for h in (0, 6, 12, 18)] + [_obs(3, h) for h in (0, 6, 12, 18)]
    notes = _data_quality_notes(observations, analysis_day=3)
    assert any("day(s): [2]" in n for n in notes)


def test_data_quality_flags_partial_day():
    observations = [_obs(1, 0), _obs(1, 6), _obs(1, 12)]  # missing hour 18
    notes = _data_quality_notes(observations, analysis_day=1)
    assert any("only 3 of 4" in n for n in notes)


def test_data_quality_flags_out_of_range_percentage_only():
    observations = [_obs(1, h) for h in (0, 6, 12, 18)]
    observations[0].humidity_pct = 150.0
    observations[1].soil_moisture_pct = -5.0
    notes = _data_quality_notes(observations, analysis_day=1)
    assert any("Humidity" in n and "150.00" in n for n in notes)
    assert any("Soil Moisture" in n and "-5.00" in n for n in notes)
    forbidden = ["stress", "deficien", "recommend", "irrigate", "fertiliz"]
    for note in notes:
        for word in forbidden:
            assert word not in note.lower()


def test_data_quality_no_notes_for_clean_complete_data():
    observations = [_obs(1, h) for h in (0, 6, 12, 18)] + [_obs(2, h) for h in (0, 6, 12, 18)]
    notes = _data_quality_notes(observations, analysis_day=2)
    assert notes == []


# ---------------------------------------------------------------------
# 6. Full-service integration tests against a real generated simulation
# ---------------------------------------------------------------------

def _make_run(db, duration_days=40, scenario="normal", seed=1, **kwargs):
    config = build_config(duration_days=duration_days, scenario=scenario, seed=seed, **kwargs)
    return create_run(db, config)


def test_analyze_run_returns_all_seven_parameters(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=40, seed=101)
        result = analyze_run(db, run.id)
        assert result.run_id == run.id
        assert result.analysis_day == 40
        assert len(result.parameters) == 7
        labels = {pa.current.parameter for pa in result.parameters}
        assert labels == {"Temperature", "Humidity", "Soil Moisture", "DLI", "Soil N", "Soil P", "Soil K"}
    finally:
        db.close()


def test_analyze_run_with_day_restricts_history(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=40, seed=202)
        result_full = analyze_run(db, run.id)
        result_day20 = analyze_run(db, run.id, day=20)
        assert result_full.analysis_day == 40
        assert result_day20.analysis_day == 20
        # trend n_observations must differ -- day=20 sees strictly less history
        temp_full = next(pa for pa in result_full.parameters if pa.current.field == "temperature_c")
        temp_day20 = next(pa for pa in result_day20.parameters if pa.current.field == "temperature_c")
        assert temp_day20.trend.n_observations < temp_full.trend.n_observations
    finally:
        db.close()


def test_analyze_run_invalid_run_id_raises(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            analyze_run(db, 9_999_999)
    finally:
        db.close()


def test_analyze_run_invalid_day_raises(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=303)
        with pytest.raises(InvalidDayError):
            analyze_run(db, run.id, day=0)
        with pytest.raises(InvalidDayError):
            analyze_run(db, run.id, day=11)
    finally:
        db.close()


def test_analyze_run_single_day_has_undetermined_persistence(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=5, seed=404)
        result = analyze_run(db, run.id, day=1)
        for pa in result.parameters:
            assert pa.persistence.days is None
    finally:
        db.close()


def test_analyze_run_isolates_multiple_runs(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run_a = _make_run(db, duration_days=15, seed=111)
        run_b = _make_run(db, duration_days=15, seed=222)
        result_a = analyze_run(db, run_a.id)
        result_b = analyze_run(db, run_b.id)
        assert result_a.run_id == run_a.id
        assert result_b.run_id == run_b.id
        temp_a = next(pa for pa in result_a.parameters if pa.current.field == "temperature_c")
        temp_b = next(pa for pa in result_b.parameters if pa.current.field == "temperature_c")
        # different seeds -> different noise draws -> current values should differ
        assert temp_a.current.value != temp_b.current.value
    finally:
        db.close()


def test_analyze_run_is_deterministic(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=20, seed=555)
        result1 = analyze_run(db, run.id)
        result2 = analyze_run(db, run.id)
        for pa1, pa2 in zip(result1.parameters, result2.parameters):
            assert pa1.current.value == pa2.current.value
            assert pa1.trend.direction == pa2.trend.direction
            assert pa1.trend.rate_per_day == pa2.trend.rate_per_day
            assert pa1.persistence.days == pa2.persistence.days
    finally:
        db.close()


def test_analyze_run_icar_deviation_matches_actual_reference(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    from app.services.simulator.baseline import load_baseline

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=47, seed=606)
        result = analyze_run(db, run.id)
        baseline = load_baseline(db)
        temp = next(pa for pa in result.parameters if pa.current.field == "temperature_c")
        expected_icar = baseline[temp.current.day].temperature_c
        assert temp.icar.icar_value == pytest.approx(expected_icar)
        assert temp.icar.signed_difference == pytest.approx(temp.current.value - expected_icar)
    finally:
        db.close()


def test_analyze_run_current_state_is_the_daily_average_not_the_last_slot(seeded_db, seeded_agronomics_db):
    """
    Core Phase 3 daily-aggregation requirement: "current state" for a
    day must be the mean of that day's available readings, not
    whichever single 6-hour slot happens to be last.
    """
    from app.database.session import SessionLocal

    from app.models.sensor_observation import SensorObservation

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=40, seed=707070)
        result = analyze_run(db, run.id)

        raw = (
            db.query(SensorObservation)
            .filter(SensorObservation.simulation_run_id == run.id, SensorObservation.day == 40)
            .order_by(SensorObservation.hour)
            .all()
        )
        assert len(raw) == 4  # the raw 4 rows are untouched
        expected_mean = sum(o.soil_moisture_pct for o in raw) / 4
        last_slot_value = raw[-1].soil_moisture_pct

        moisture = next(pa for pa in result.parameters if pa.current.field == "soil_moisture_pct")
        assert moisture.current.value == pytest.approx(expected_mean)
        assert moisture.current.value != pytest.approx(last_slot_value)
        assert moisture.current.n_readings == 4
    finally:
        db.close()


def test_analyze_run_trend_uses_one_point_per_day_not_per_slot(seeded_db, seeded_agronomics_db):
    """
    A day's 4 raw 6-hour observations must never be treated as 4
    separate days by the trend regression.
    """
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=10, seed=808080)
        result = analyze_run(db, run.id, day=5)
        for pa in result.parameters:
            assert pa.trend.n_observations == 5  # 5 days, NOT 5*4=20 slots
    finally:
        db.close()


def test_analyze_run_icar_deviation_uses_daily_state_not_a_single_slot(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    from app.models.sensor_observation import SensorObservation
    from app.services.simulator.baseline import load_baseline

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=40, seed=909090)
        result = analyze_run(db, run.id)
        baseline = load_baseline(db)

        raw = (
            db.query(SensorObservation)
            .filter(SensorObservation.simulation_run_id == run.id, SensorObservation.day == 40)
            .all()
        )
        expected_daily_temp = sum(o.temperature_c for o in raw) / len(raw)

        temp = next(pa for pa in result.parameters if pa.current.field == "temperature_c")
        assert temp.icar.current_value == pytest.approx(expected_daily_temp)
        expected_icar = baseline[40].temperature_c
        assert temp.icar.signed_difference == pytest.approx(expected_daily_temp - expected_icar)
    finally:
        db.close()


def test_40_day_run_produces_160_observations_and_40_daily_history_records(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    from app.models.sensor_observation import SensorObservation
    from app.models.state_analysis_history import StateAnalysisHistory

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=40, seed=404040)  # create_run auto-persists Phase 3 history
        obs_count = (
            db.query(SensorObservation).filter(SensorObservation.simulation_run_id == run.id).count()
        )
        history_count = (
            db.query(StateAnalysisHistory).filter(StateAnalysisHistory.simulation_run_id == run.id).count()
        )
        assert obs_count == 160
        assert history_count == 40
    finally:
        db.close()


def test_analyze_run_day_100_reports_both_overlapping_stages(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=120, seed=707)
        result = analyze_run(db, run.id, day=100)
        names = {s.name for s in result.crop_stages}
        assert "kc_mid_stage" in names
        assert "kc_late_stage" in names
    finally:
        db.close()


def test_analyze_run_temperature_domain_has_no_day_resolvable_context(seeded_db, seeded_agronomics_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=30, seed=808)
        result = analyze_run(db, run.id, day=15)  # inside kc_initial_stage
        temp_domain_items = [i for i in result.agronomic_context if i.domain == "temperature"]
        assert temp_domain_items == []
    finally:
        db.close()


# ---------------------------------------------------------------------
# 7. API tests
# ---------------------------------------------------------------------

def test_api_state_analysis_returns_full_structure(api_client):
    create_resp = api_client.post(
        "/api/simulator/runs",
        json={"duration_days": 30, "scenario": "normal", "seed": 42},
    )
    assert create_resp.status_code == 201
    run_id = create_resp.json()["id"]

    resp = api_client.get(f"/api/analysis/tomato/runs/{run_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run_id
    assert len(body["parameters"]) == 7
    assert "crop_stages" in body
    assert "agronomic_context" in body
    assert "data_quality_notes" in body


def test_api_state_analysis_day_query_param(api_client):
    create_resp = api_client.post(
        "/api/simulator/runs",
        json={"duration_days": 30, "scenario": "normal", "seed": 43},
    )
    run_id = create_resp.json()["id"]

    resp = api_client.get(f"/api/analysis/tomato/runs/{run_id}?day=10")
    assert resp.status_code == 200
    assert resp.json()["analysis_day"] == 10


def test_api_state_analysis_404_for_nonexistent_run(api_client):
    resp = api_client.get("/api/analysis/tomato/runs/9999999")
    assert resp.status_code == 404


def test_api_state_analysis_422_for_invalid_day(api_client):
    create_resp = api_client.post(
        "/api/simulator/runs",
        json={"duration_days": 10, "scenario": "normal", "seed": 44},
    )
    run_id = create_resp.json()["id"]
    resp = api_client.get(f"/api/analysis/tomato/runs/{run_id}?day=999")
    assert resp.status_code == 422


def test_cli_and_api_agree_on_underlying_analysis(seeded_db, seeded_agronomics_db, api_client):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=25, seed=909)
    finally:
        db.close()

    service_result = None
    db2 = SessionLocal()
    try:
        service_result = analyze_run(db2, run.id)
    finally:
        db2.close()

    api_resp = api_client.get(f"/api/analysis/tomato/runs/{run.id}")
    api_body = api_resp.json()

    assert api_body["analysis_day"] == service_result.analysis_day
    api_temp = next(p for p in api_body["parameters"] if p["current"]["field"] == "temperature_c")
    service_temp = next(p for p in service_result.parameters if p.current.field == "temperature_c")
    assert api_temp["current"]["value"] == pytest.approx(service_temp.current.value)
    assert api_temp["trend"]["direction"] == service_temp.trend.direction


# ---------------------------------------------------------------------
# 8. Structural guards
# ---------------------------------------------------------------------

def test_cli_contains_no_analysis_calculation_logic():
    source = inspect.getsource(__import__("app.state_analysis_cli", fromlist=["x"]))
    forbidden_fragments = [
        "def compute_trend(",
        "def compute_persistence(",
        "def compute_icar_deviation(",
        "def resolve_crop_stages(",
        "sxx",
        "sxy",
        "residual_variance",
        "STABILITY_K",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in source, f"CLI appears to duplicate analysis logic: {fragment!r} found"
    assert "from app.services.state_analysis.service import" in source


def test_route_contains_no_analysis_calculation_logic():
    from app import routes

    source = inspect.getsource(routes.state_analysis)
    forbidden_fragments = ["sxx", "sxy", "residual_variance", "def compute_trend("]
    for fragment in forbidden_fragments:
        assert fragment not in source
    assert "from app.services.state_analysis.service import" in source


def test_state_analysis_package_never_imports_simulator_internals():
    """
    Phase 3 must stay usable against a future real-sensor feed -- it may
    reuse app.services.simulator.baseline (the read-only ICAR loader)
    but must never depend on the simulator's own generation internals.
    """
    modules = [service, trend, persistence, icar_deviation, crop_stage_context]
    forbidden_imports = [
        "simulator.generator",
        "simulator.causal_model",
        "simulator.calibration",
        "simulator.scenarios",
        "simulator.rng",
        "simulator.constants",
        "simulation_internal_state",
    ]
    for module in modules:
        source = inspect.getsource(module)
        for fragment in forbidden_imports:
            assert fragment not in source, f"{module.__name__} references simulator-internal {fragment!r}"


def test_no_diagnosis_or_recommendation_vocabulary_anywhere_in_phase3():
    from app import state_analysis_cli

    modules = [service, trend, persistence, icar_deviation, crop_stage_context, state_analysis_cli]
    forbidden_words = [
        "stress", "deficien", "recommend", "irrigate now", "increase irrigation",
        "reduce irrigation", "apply fertilizer", "recommended action", "pump",
        "optimi",
    ]
    for module in modules:
        source = inspect.getsource(module).lower()
        for word in forbidden_words:
            assert word not in source, f"{module.__name__} contains forbidden vocabulary: {word!r}"


def test_no_diagnosis_vocabulary_in_actual_rendered_cli_output(seeded_db, seeded_agronomics_db, capsys):
    from app import state_analysis_cli

    db = None
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        run = _make_run(db, duration_days=40, scenario="heatwave", seed=1010, severity="severe",
                         scenario_start_day=10, scenario_duration_days=10)
        run_id = run.id
        from app.services.state_analysis.history import persist_run_history

        persist_run_history(db, run_id)
    finally:
        db.close()

    exit_code = state_analysis_cli.main(["--run-id", str(run_id)])
    assert exit_code == 0
    out = capsys.readouterr().out.lower()
    forbidden_phrases = [
        "stress detected", "water stress", "heat stress", "nutrient deficiency",
        "irrigate now", "increase irrigation", "reduce irrigation",
        "apply fertilizer", "recommended action",
    ]
    for phrase in forbidden_phrases:
        assert phrase not in out
