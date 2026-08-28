"""
Pure-function tests for app.services.state_analysis.daily_aggregation
-- the module that turns Phase 2's 4 raw 6-hour sensor_observations
rows/day into ONE representative daily value, without touching those
raw rows at all.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.services.state_analysis.daily_aggregation import aggregate_daily


def _obs(day, hour, **fields):
    base = dict(
        temperature_c=None, humidity_pct=None, soil_moisture_pct=None,
        daily_dli_mol_m2_day=None, soil_n_mg_kg=None, soil_p_mg_kg=None, soil_k_mg_kg=None,
    )
    base.update(fields)
    return SimpleNamespace(day=day, hour=hour, **base)


def test_four_readings_produce_exactly_one_daily_value():
    observations = [_obs(40, h, soil_moisture_pct=v) for h, v in zip((0, 6, 12, 18), (60, 58, 55, 52))]
    result = aggregate_daily(observations, "soil_moisture_pct")
    assert len(result) == 1
    assert result[0].day == 40


def test_soil_moisture_averaged_correctly():
    observations = [_obs(40, h, soil_moisture_pct=v) for h, v in zip((0, 6, 12, 18), (60, 58, 55, 52))]
    result = aggregate_daily(observations, "soil_moisture_pct")
    assert result[0].value == 56.25
    assert result[0].n_readings == 4


def test_temperature_averaged_correctly():
    observations = [_obs(1, h, temperature_c=v) for h, v in zip((0, 6, 12, 18), (20.0, 24.0, 28.0, 22.0))]
    result = aggregate_daily(observations, "temperature_c")
    assert result[0].value == 23.5


def test_humidity_averaged_correctly():
    observations = [_obs(1, h, humidity_pct=v) for h, v in zip((0, 6, 12, 18), (50.0, 60.0, 70.0, 80.0))]
    result = aggregate_daily(observations, "humidity_pct")
    assert result[0].value == 65.0


def test_npk_averaged_correctly():
    observations = [
        _obs(1, h, soil_n_mg_kg=n, soil_p_mg_kg=p, soil_k_mg_kg=k)
        for h, n, p, k in zip((0, 6, 12, 18), (100, 110, 120, 130), (10, 20, 30, 40), (200, 210, 220, 230))
    ]
    assert aggregate_daily(observations, "soil_n_mg_kg")[0].value == 115.0
    assert aggregate_daily(observations, "soil_p_mg_kg")[0].value == 25.0
    assert aggregate_daily(observations, "soil_k_mg_kg")[0].value == 215.0


def test_dli_uses_the_duplicated_value_not_an_average():
    observations = [_obs(5, h, daily_dli_mol_m2_day=20.0) for h in (0, 6, 12, 18)]
    result = aggregate_daily(observations, "daily_dli_mol_m2_day")
    assert result[0].value == 20.0
    assert result[0].note is None  # all 4 copies agree -- nothing to flag


def test_dli_disagreement_is_flagged_not_silently_averaged():
    """
    If the 4 duplicated DLI copies ever disagreed (should not happen
    from the simulator, but the analysis layer must not assume that),
    the FIRST available reading is used as the representative value --
    never an average of physically-meaningless duplicate copies -- and
    the disagreement is reported explicitly.
    """
    observations = [_obs(5, h, daily_dli_mol_m2_day=v) for h, v in zip((0, 6, 12, 18), (20.0, 20.0, 25.0, 20.0))]
    result = aggregate_daily(observations, "daily_dli_mol_m2_day")
    assert result[0].value == 20.0  # first reading, NOT mean(20,20,25,20) == 21.25
    assert result[0].note is not None
    assert "disagree" in result[0].note


def test_missing_readings_reduce_the_denominator_not_crash():
    observations = [_obs(1, h, soil_moisture_pct=v) for h, v in zip((0, 6, 12), (60.0, 58.0, 55.0))]  # hour 18 missing
    result = aggregate_daily(observations, "soil_moisture_pct")
    assert result[0].n_readings == 3
    assert result[0].value == (60.0 + 58.0 + 55.0) / 3


def test_day_with_zero_readings_for_a_field_is_simply_absent():
    observations = [_obs(1, 0, temperature_c=20.0)]  # soil_moisture_pct never set (None)
    result = aggregate_daily(observations, "soil_moisture_pct")
    assert result == []


def test_multiple_days_each_produce_their_own_daily_value_sorted_ascending():
    observations = (
        [_obs(2, h, temperature_c=30.0) for h in (0, 6, 12, 18)]
        + [_obs(1, h, temperature_c=20.0) for h in (0, 6, 12, 18)]
    )
    result = aggregate_daily(observations, "temperature_c")
    assert [dv.day for dv in result] == [1, 2]
    assert result[0].value == 20.0
    assert result[1].value == 30.0
