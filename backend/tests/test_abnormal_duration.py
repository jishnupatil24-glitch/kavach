"""
Tests for abnormal_state_duration -- a SEPARATE concept from Phase 3's
own persistence_days (trend-step continuation, unchanged). See
app.services.stress_assessment.abnormal_duration's own docstring for
the two-tier definition.

The two regression tests below pin the exact values verified by hand
during the design audit against the real excess_irrigation and
water_shortage runs (same scenario/seed/timing as the runs already
persisted in the project database as run_id 2 and run_id 1) -- proving
the implementation reproduces the audited numbers, not just plausible
ones.
"""
from __future__ import annotations

from app.database.session import SessionLocal
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis.service import ParameterAnalysis
from app.services.state_analysis.current_state import CurrentState
from app.services.state_analysis.icar_deviation import IcarDeviation
from app.services.state_analysis.persistence import PersistenceResult
from app.services.state_analysis.trend import TrendResult
from app.services.stress_assessment.abnormal_duration import (
    NO_RUN_CONTEXT_NOTE,
    TIER2_PROVENANCE_NOTE,
    TIER_ICAR_SIGN_TREND_PROXY,
    TIER_SOURCED_THRESHOLD,
    classify_tier,
)
from app.services.stress_assessment.categories import CATEGORIES
from app.services.stress_assessment.evidence import compute_problem_assessment
from app.services.stress_assessment.service import assess_run


def _category(key):
    return next(c for c in CATEGORIES if c.key == key)


def _find(problems, category_key):
    return next(p for p in problems if p.category == category_key)


# ---------------------------------------------------------------------
# 1. Tier classification is static (category-only, no DB/run needed)
# ---------------------------------------------------------------------

def test_tier1_categories_are_sourced_threshold():
    for key in ("heat_related", "humidity_low", "humidity_high"):
        assert classify_tier(key) == TIER_SOURCED_THRESHOLD


def test_tier2_categories_are_icar_sign_trend_proxy():
    for key in (
        "water_depletion", "excessive_moisture", "temperature_deficit",
        "nitrogen_related", "phosphorus_related", "potassium_related", "light_deficit",
    ):
        assert classify_tier(key) == TIER_ICAR_SIGN_TREND_PROXY


# ---------------------------------------------------------------------
# 2. compute_problem_assessment without run context (existing 5-arg
#    call sites, e.g. every pre-existing test in
#    test_stress_assessment*.py) must keep working unchanged, and must
#    report abnormal_state_duration honestly as "not computed" rather
#    than crash or silently guess.
# ---------------------------------------------------------------------

def test_no_run_context_reports_not_computed_not_a_crash():
    pa = ParameterAnalysis(
        current=CurrentState(parameter="X", field="soil_moisture_pct", value=60.0, day=10, n_readings=4, note=None),
        trend=TrendResult(parameter="X", direction="FALLING", rate_per_day=-1.0, rate_unit="pp/day",
                           standard_error_per_day=0.3, stable_band=0.6, n_observations=10, note=None),
        persistence=PersistenceResult(parameter="X", direction="FALLING", days=3, note=None),
        icar=IcarDeviation(parameter="X", current_value=60.0, icar_value=70.0, icar_day=10,
                            signed_difference=-10.0, absolute_difference=10.0, unit_suffix=" %", note=None),
    )
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    # existing field, existing behavior -- unchanged
    assert result.persistence_days == 3
    # new field, honest about missing context
    assert result.abnormal_state_duration.days is None
    assert result.abnormal_state_duration.tier == TIER_ICAR_SIGN_TREND_PROXY
    assert result.abnormal_state_duration.provenance_note == NO_RUN_CONTEXT_NOTE


def test_tier2_provenance_note_present_with_run_context(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        config = build_config(duration_days=10, scenario="normal", seed=42001)
        run = create_run(db, config)
        result = assess_run(db, run.id, day=10)
        water = _find(result.problems, "water_depletion")
        assert water.abnormal_state_duration.tier == TIER_ICAR_SIGN_TREND_PROXY
        assert water.abnormal_state_duration.provenance_note == TIER2_PROVENANCE_NOTE
        assert water.abnormal_state_duration.days is not None
    finally:
        db.close()


# ---------------------------------------------------------------------
# 3. Regression: the two verified real-run numbers from the design audit
# ---------------------------------------------------------------------

def test_excess_irrigation_run_day38_abnormal_duration_matches_audit():
    """
    Same scenario/seed/timing as the project's real excess_irrigation
    run (run_id 2 in the project database): duration 38, seed 123456,
    scenario_start_day 27, scenario_duration_days 9. Deterministic RNG
    reproduces identical sensor data.

    Audited by hand: excessive_moisture's trend turns RISING at day 30
    and its ICAR-deviation sign is already + from day 29 -- the
    combined predicate (trend RISING AND icar sign +) holds for days
    30-38 inclusive = 9 days, breaking at day 29 (trend STABLE there).
    persistence_days (trend-step continuation, unrelated concept) is 1
    on day 38 because the day 37->38 step is a small negative delta
    against a RISING direction.
    """
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)

        result = assess_run(db, run.id, day=38)
        excess = _find(result.problems, "excessive_moisture")

        assert excess.persistence_days == 1  # unchanged, existing Phase 3 concept
        assert excess.abnormal_state_duration.days == 9  # new concept
        assert excess.abnormal_state_duration.tier == TIER_ICAR_SIGN_TREND_PROXY
    finally:
        db.close()


def test_water_shortage_run_day40_abnormal_duration_matches_audit():
    """
    Same scenario/seed/timing as the project's real water_shortage run
    (run_id 1): duration 40, seed 1234, scenario_start_day 31,
    scenario_duration_days 8.

    Audited by hand: water_depletion's trend is FALLING for the entire
    day 20-40 window and its ICAR-deviation sign flips to - at day 31,
    staying - through day 40 = 10 days, breaking at day 30 (sign still
    + there). persistence_days is 1 on day 40 (the day 39->40 step
    falls below the trend's own stable_band even though both days sit
    on the deficit side of ICAR).
    """
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=40, scenario="water_shortage", seed=1234,
            severity="severe", scenario_start_day=31, scenario_duration_days=8,
        )
        run = create_run(db, config)

        result = assess_run(db, run.id, day=40)
        depletion = _find(result.problems, "water_depletion")

        assert depletion.persistence_days == 1  # unchanged, existing Phase 3 concept
        assert depletion.abnormal_state_duration.days == 10  # new concept
        assert depletion.abnormal_state_duration.tier == TIER_ICAR_SIGN_TREND_PROXY
    finally:
        db.close()


def test_excess_irrigation_persistence_days_across_history_unchanged():
    """
    Full-history regression pin: persistence_days for every day in the
    audited 25-38 window must match the exact values captured live
    during the design audit, proving this feature made zero change to
    Phase 3's existing persistence.py output.
    """
    expected = {25: 2, 26: 3, 27: 1, 28: 1, 29: 1, 30: 5, 31: 1, 32: 1,
                33: 1, 34: 1, 35: 1, 36: 1, 37: 1, 38: 1}
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)

        for day, expected_persistence in expected.items():
            result = assess_run(db, run.id, day=day)
            excess = _find(result.problems, "excessive_moisture")
            assert excess.persistence_days == expected_persistence, f"day {day}"
    finally:
        db.close()


# ---------------------------------------------------------------------
# 4. Tier 1 (sourced threshold) sanity: humidity/heat categories don't
#    silently fall back to the Tier 2 proxy behavior.
# ---------------------------------------------------------------------

def test_tier1_category_uses_sourced_threshold_not_icar_sign(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=40, scenario="heatwave", seed=123,
            severity="severe", scenario_start_day=31, scenario_duration_days=10,
        )
        run = create_run(db, config)
        result = assess_run(db, run.id, day=40)
        heat = _find(result.problems, "heat_related")
        assert heat.abnormal_state_duration.tier == TIER_SOURCED_THRESHOLD
        assert "sourced" in heat.abnormal_state_duration.provenance_note.lower()
        assert TIER2_PROVENANCE_NOTE not in heat.abnormal_state_duration.provenance_note
    finally:
        db.close()


# ---------------------------------------------------------------------
# 5. CLI clearly distinguishes the two labels
# ---------------------------------------------------------------------

def test_cli_distinguishes_trend_persistence_from_abnormal_duration(capsys):
    from app import stress_assessment_cli

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

    stress_assessment_cli.main(["--run-id", str(run_id), "--day", "38"])
    out = capsys.readouterr().out
    assert "Trend Persistence:" in out
    assert "Abnormal-State Duration:" in out
    assert "9 days" in out  # excessive_moisture's abnormal duration on day 38
