import pytest

from app.services.simulator.baseline import load_baseline
from app.services.simulator.config import SimulationConfigError, build_config
from app.services.simulator.generator import generate


@pytest.fixture(scope="module")
def baseline(seeded_db):
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        return load_baseline(db)
    finally:
        db.close()


# --- config validation ---------------------------------------------------

def test_duration_must_be_within_icar_span():
    with pytest.raises(SimulationConfigError):
        build_config(duration_days=0, scenario="normal", seed=1)
    with pytest.raises(SimulationConfigError):
        build_config(duration_days=121, scenario="normal", seed=1)
    build_config(duration_days=1, scenario="normal", seed=1)
    build_config(duration_days=120, scenario="normal", seed=1)


def test_normal_scenario_rejects_severity_and_window():
    with pytest.raises(SimulationConfigError):
        build_config(duration_days=10, scenario="normal", seed=1, severity="mild")
    with pytest.raises(SimulationConfigError):
        build_config(duration_days=10, scenario="normal", seed=1, scenario_start_day=1, scenario_duration_days=2)


def test_non_normal_scenario_requires_severity_and_window():
    with pytest.raises(SimulationConfigError):
        build_config(duration_days=10, scenario="heatwave", seed=1)
    with pytest.raises(SimulationConfigError):
        build_config(duration_days=10, scenario="heatwave", seed=1, severity="mild")


def test_scenario_window_cannot_exceed_duration():
    with pytest.raises(SimulationConfigError):
        build_config(
            duration_days=10, scenario="heatwave", seed=1, severity="mild",
            scenario_start_day=9, scenario_duration_days=5,
        )
    with pytest.raises(SimulationConfigError):
        build_config(
            duration_days=10, scenario="heatwave", seed=1, severity="mild",
            scenario_start_day=15, scenario_duration_days=1,
        )


# --- row shape / count -----------------------------------------------------

def test_observation_count_and_day_hour_coverage(baseline):
    config = build_config(duration_days=53, scenario="normal", seed=1)
    slots = generate(config, baseline)
    assert len(slots) == 53 * 4
    days = sorted({s.day for s in slots})
    assert days == list(range(1, 54))
    for day in days:
        hours = sorted(s.hour for s in slots if s.day == day)
        assert hours == [0, 6, 12, 18]


def test_daily_dli_is_one_value_per_day_not_four_independent_readings(baseline):
    config = build_config(duration_days=5, scenario="normal", seed=1)
    slots = generate(config, baseline)
    for day in range(1, 6):
        dli_values = {s.daily_dli_mol_m2_day for s in slots if s.day == day}
        assert len(dli_values) == 1, f"day {day} has non-uniform DLI across its 4 slots: {dli_values}"
        assert dli_values.pop() == baseline[day].dli_mol_m2_day


# --- determinism / seed sensitivity -----------------------------------------

def test_same_config_is_deterministic(baseline):
    config = build_config(duration_days=20, scenario="normal", seed=99)
    a = generate(config, baseline)
    b = generate(config, baseline)
    assert [(s.day, s.hour, s.temperature_c, s.humidity_pct, s.soil_moisture_pct, s.soil_n_mg_kg) for s in a] == [
        (s.day, s.hour, s.temperature_c, s.humidity_pct, s.soil_moisture_pct, s.soil_n_mg_kg) for s in b
    ]


def test_different_seed_produces_different_output(baseline):
    a = generate(build_config(duration_days=20, scenario="normal", seed=1), baseline)
    b = generate(build_config(duration_days=20, scenario="normal", seed=2), baseline)
    assert any(x.temperature_c != y.temperature_c for x, y in zip(a, b))


# --- causal consistency across scenarios ------------------------------------

def _mean(values):
    values = list(values)
    return sum(values) / len(values)


def test_heatwave_raises_temperature_and_accelerates_moisture_decline(baseline):
    seed = 5
    normal = generate(build_config(duration_days=10, scenario="normal", seed=seed), baseline)
    heat = generate(
        build_config(duration_days=10, scenario="heatwave", seed=seed, severity="severe",
                     scenario_start_day=3, scenario_duration_days=3),
        baseline,
    )

    normal_temp_d4 = _mean(s.temperature_c for s in normal if s.day == 4)
    heat_temp_d4 = _mean(s.temperature_c for s in heat if s.day == 4)
    assert heat_temp_d4 > normal_temp_d4  # scenario actually raised temperature

    normal_moisture_d10 = _mean(s.soil_moisture_pct for s in normal if s.day == 10)
    heat_moisture_d10 = _mean(s.soil_moisture_pct for s in heat if s.day == 10)
    assert heat_moisture_d10 < normal_moisture_d10  # heat causally accelerated moisture decline

    # No independent randomness: outside the scenario window, both runs
    # (same seed) must have identical temperature -- heatwave affects
    # only its own window plus the documented 1-day ramps.
    for s_normal, s_heat in zip(normal, heat):
        if s_normal.day < 3 or s_normal.day > 6:
            assert s_normal.temperature_c == s_heat.temperature_c


def test_water_shortage_reduces_moisture_without_touching_temperature(baseline):
    seed = 5
    normal = generate(build_config(duration_days=10, scenario="normal", seed=seed), baseline)
    shortage = generate(
        build_config(duration_days=10, scenario="water_shortage", seed=seed, severity="severe",
                     scenario_start_day=3, scenario_duration_days=3),
        baseline,
    )

    normal_moisture_d10 = _mean(s.soil_moisture_pct for s in normal if s.day == 10)
    shortage_moisture_d10 = _mean(s.soil_moisture_pct for s in shortage if s.day == 10)
    assert shortage_moisture_d10 < normal_moisture_d10

    # Water shortage has exactly one cause (reduced irrigation) -- it
    # must never alter temperature or humidity.
    for s_normal, s_shortage in zip(normal, shortage):
        assert s_normal.temperature_c == s_shortage.temperature_c
        assert s_normal.humidity_pct == s_shortage.humidity_pct


def test_excess_irrigation_raises_moisture_toward_ceiling(baseline):
    seed = 5
    normal = generate(build_config(duration_days=10, scenario="normal", seed=seed), baseline)
    excess = generate(
        build_config(duration_days=10, scenario="excess_irrigation", seed=seed, severity="severe",
                     scenario_start_day=3, scenario_duration_days=5),
        baseline,
    )
    normal_moisture_d8 = _mean(s.soil_moisture_pct for s in normal if s.day == 8)
    excess_moisture_d8 = _mean(s.soil_moisture_pct for s in excess if s.day == 8)
    assert excess_moisture_d8 > normal_moisture_d8
    assert all(s.soil_moisture_pct <= 100.0 for s in excess)  # safety ceiling holds


def test_high_humidity_raises_humidity_without_touching_moisture_directly(baseline):
    seed = 5
    normal = generate(build_config(duration_days=10, scenario="normal", seed=seed), baseline)
    humid = generate(
        build_config(duration_days=10, scenario="high_humidity", seed=seed, severity="severe",
                     scenario_start_day=3, scenario_duration_days=3),
        baseline,
    )
    normal_humidity_d4 = _mean(s.humidity_pct for s in normal if s.day == 4)
    humid_humidity_d4 = _mean(s.humidity_pct for s in humid if s.day == 4)
    assert humid_humidity_d4 > normal_humidity_d4

    for s_normal, s_humid in zip(normal, humid):
        assert s_normal.temperature_c == s_humid.temperature_c


def test_moisture_never_leaves_valid_range(baseline):
    config = build_config(
        duration_days=60, scenario="excess_irrigation", seed=3, severity="severe",
        scenario_start_day=1, scenario_duration_days=60,
    )
    slots = generate(config, baseline)
    assert all(0.0 <= s.soil_moisture_pct <= 100.0 for s in slots)


def test_humidity_never_leaves_valid_range(baseline):
    config = build_config(
        duration_days=30, scenario="high_humidity", seed=3, severity="severe",
        scenario_start_day=1, scenario_duration_days=30,
    )
    slots = generate(config, baseline)
    assert all(0.0 <= s.humidity_pct <= 100.0 for s in slots)


def test_normal_scenario_stays_reasonably_close_to_icar_trajectory(baseline):
    """
    Sanity check on the NORMAL-scenario calibration (approved
    requirement): it should track the ICAR trajectory approximately,
    not exactly (never forced), and not drift wildly.
    """
    config = build_config(duration_days=60, scenario="normal", seed=11)
    slots = generate(config, baseline)
    for day in range(1, 61):
        simulated_mean = _mean(s.soil_moisture_pct for s in slots if s.day == day)
        icar_value = baseline[day].soil_moisture_pct
        assert abs(simulated_mean - icar_value) < 6.0, (
            f"day {day}: simulated {simulated_mean:.2f} vs ICAR {icar_value} diverged too far"
        )


# --- API ---------------------------------------------------------------

def test_api_create_and_retrieve_normal_run(api_client):
    resp = api_client.post(
        "/api/simulator/runs",
        json={"duration_days": 5, "scenario": "normal", "seed": 42},
    )
    assert resp.status_code == 201
    run = resp.json()
    assert run["duration_days"] == 5
    assert run["scenario"] == "normal"
    assert run["severity"] is None

    run_id = run["id"]
    resp2 = api_client.get(f"/api/simulator/runs/{run_id}")
    assert resp2.status_code == 200
    assert resp2.json()["id"] == run_id

    resp3 = api_client.get(f"/api/simulator/runs/{run_id}/observations")
    assert resp3.status_code == 200
    observations = resp3.json()
    assert len(observations) == 20
    assert {o["hour"] for o in observations} == {0, 6, 12, 18}
    assert {o["day"] for o in observations} == {1, 2, 3, 4, 5}


def test_api_create_run_reproducible_via_same_config(api_client):
    payload = {"duration_days": 4, "scenario": "normal", "seed": 777}
    r1 = api_client.post("/api/simulator/runs", json=payload).json()
    r2 = api_client.post("/api/simulator/runs", json=payload).json()
    assert r1["id"] != r2["id"]  # each POST creates a new run, no dedup

    obs1 = api_client.get(f"/api/simulator/runs/{r1['id']}/observations").json()
    obs2 = api_client.get(f"/api/simulator/runs/{r2['id']}/observations").json()
    key = lambda o: (o["day"], o["hour"])
    obs1_sorted = sorted(obs1, key=key)
    obs2_sorted = sorted(obs2, key=key)
    for o1, o2 in zip(obs1_sorted, obs2_sorted):
        assert o1["temperature_c"] == o2["temperature_c"]
        assert o1["soil_moisture_pct"] == o2["soil_moisture_pct"]


def test_api_rejects_out_of_range_duration(api_client):
    resp = api_client.post(
        "/api/simulator/runs",
        json={"duration_days": 121, "scenario": "normal", "seed": 1},
    )
    assert resp.status_code == 422


def test_api_rejects_missing_severity_for_non_normal_scenario(api_client):
    resp = api_client.post(
        "/api/simulator/runs",
        json={"duration_days": 10, "scenario": "heatwave", "seed": 1},
    )
    assert resp.status_code == 422


def test_api_heatwave_run_end_to_end(api_client):
    resp = api_client.post(
        "/api/simulator/runs",
        json={
            "duration_days": 10, "scenario": "heatwave", "severity": "severe",
            "seed": 5, "scenario_start_day": 3, "scenario_duration_days": 3,
        },
    )
    assert resp.status_code == 201
    run_id = resp.json()["id"]
    observations = api_client.get(f"/api/simulator/runs/{run_id}/observations").json()
    assert len(observations) == 40

    normal_resp = api_client.post(
        "/api/simulator/runs", json={"duration_days": 10, "scenario": "normal", "seed": 5}
    )
    normal_observations = api_client.get(
        f"/api/simulator/runs/{normal_resp.json()['id']}/observations"
    ).json()

    day4_heat = [o["temperature_c"] for o in observations if o["day"] == 4]
    day4_normal = [o["temperature_c"] for o in normal_observations if o["day"] == 4]
    assert sum(day4_heat) / len(day4_heat) > sum(day4_normal) / len(day4_normal)


def test_api_run_not_found(api_client):
    assert api_client.get("/api/simulator/runs/999999").status_code == 404
    assert api_client.get("/api/simulator/runs/999999/observations").status_code == 404


def test_api_observations_filterable_by_day(api_client):
    resp = api_client.post(
        "/api/simulator/runs", json={"duration_days": 5, "scenario": "normal", "seed": 3}
    )
    run_id = resp.json()["id"]
    observations = api_client.get(f"/api/simulator/runs/{run_id}/observations?day=3").json()
    assert len(observations) == 4
    assert all(o["day"] == 3 for o in observations)


# --- Phase 0/1/1.5C still intact --------------------------------------------

def test_phase0_and_phase1_endpoints_still_work_after_phase2(api_client):
    assert api_client.get("/health").status_code == 200
    assert api_client.get("/api/reference/tomato/day/47").status_code == 200
    assert api_client.get("/api/agronomics/tomato/sources").status_code == 200
