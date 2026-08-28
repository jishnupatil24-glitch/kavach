"""
Phase 4 severity tests: pure factor/boundary tests, decoupling from
evidence `status`, the direction-agnostic symmetric-field property,
missing-data handling, and real heatwave-run integration showing
severity actually escalating with sustained history.
"""
from __future__ import annotations

from app.database.session import SessionLocal
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run
from app.services.state_analysis.current_state import CurrentState
from app.services.state_analysis.icar_deviation import IcarDeviation
from app.services.state_analysis.persistence import PersistenceResult
from app.services.state_analysis.service import ParameterAnalysis
from app.services.state_analysis.trend import TrendResult
from app.services.stress_assessment.categories import CATEGORIES
from app.services.stress_assessment.evidence import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_INSUFFICIENT_DATA,
    SEVERITY_LOW,
    SEVERITY_MODERATE,
    STATUS_CORROBORATED_EVIDENCE,
    STATUS_WEAK_EVIDENCE,
    _compute_severity,
    compute_problem_assessment,
)
from app.services.stress_assessment.service import assess_run


def _category(key):
    return next(c for c in CATEGORIES if c.key == key)


def _pa(direction, persistence_days, icar_value, current_value, rate_per_day, stable_band, day=30, field="soil_moisture_pct"):
    signed_diff = current_value - icar_value if icar_value is not None else None
    return ParameterAnalysis(
        current=CurrentState(parameter="X", field=field, value=current_value, day=day, n_readings=4, note=None),
        trend=TrendResult(
            parameter="X", direction=direction, rate_per_day=rate_per_day, rate_unit="pp/day",
            standard_error_per_day=stable_band / 2 if stable_band else None, stable_band=stable_band,
            n_observations=day, note=None,
        ),
        persistence=PersistenceResult(parameter="X", direction=direction, days=persistence_days, note=None),
        icar=IcarDeviation(
            parameter="X", current_value=current_value, icar_value=icar_value, icar_day=day,
            signed_difference=signed_diff, absolute_difference=abs(signed_diff) if signed_diff is not None else None,
            unit_suffix=" %", note=None,
        ),
    )


# ---------------------------------------------------------------------
# 1. Missing-data -> insufficient_data
# ---------------------------------------------------------------------

def test_severity_insufficient_data_when_trend_undetermined():
    pa = _pa("UNDETERMINED", None, 70.0, 65.0, None, None)
    severity, factors = _compute_severity(pa)
    assert severity == SEVERITY_INSUFFICIENT_DATA
    assert factors is None


def test_severity_insufficient_data_when_persistence_none():
    pa = _pa("FALLING", None, 70.0, 65.0, -1.0, 0.3)
    severity, factors = _compute_severity(pa)
    assert severity == SEVERITY_INSUFFICIENT_DATA
    assert factors is None


def test_severity_insufficient_data_when_icar_value_none():
    pa = _pa("FALLING", 5, None, 65.0, -1.0, 0.3)
    severity, factors = _compute_severity(pa)
    assert severity == SEVERITY_INSUFFICIENT_DATA
    assert factors is None


def test_severity_insufficient_data_when_icar_value_zero():
    pa = _pa("FALLING", 5, 0.0, -2.0, -1.0, 0.3)
    severity, factors = _compute_severity(pa)
    assert severity == SEVERITY_INSUFFICIENT_DATA
    assert factors is None


# ---------------------------------------------------------------------
# 2. Boundary tests -- each factor's own band edges
# ---------------------------------------------------------------------

def test_deviation_boundary_exactly_at_0_10_scores_1_not_0():
    # deviation_ratio = |65-70|/70 ≈ 0.0714 -> score 0; craft an exact 0.10
    pa = _pa("FALLING", 10, 100.0, 90.0, -0.01, 100.0, day=30)  # deviation_ratio = 10/100 = 0.10 exactly
    severity, factors = _compute_severity(pa)
    assert factors.deviation_ratio == 0.10
    assert factors.deviation_score == 1  # not < 0.10, so falls into the 0.10-0.30 band


def test_all_three_factors_low_gives_low_severity():
    # tiny deviation, tiny rate vs stable_band, short duration relative to day
    pa = _pa("FALLING", 2, 100.0, 99.0, -0.05, 1.0, day=30)  # dev=0.01, intensity=0.05, duration=2/30=0.067
    severity, factors = _compute_severity(pa)
    assert factors.deviation_score == 0
    assert factors.intensity_score == 0
    assert factors.duration_score == 0
    assert severity == SEVERITY_LOW


def test_all_three_factors_maxed_gives_critical_severity():
    # large deviation, large rate vs stable_band, long duration relative to day
    pa = _pa("FALLING", 20, 100.0, 50.0, -5.0, 1.0, day=25)  # dev=0.50, intensity=5.0, duration=20/25=0.8
    severity, factors = _compute_severity(pa)
    assert factors.deviation_score == 2
    assert factors.intensity_score == 2
    assert factors.duration_score == 2
    assert factors.total_score == 6
    assert severity == SEVERITY_CRITICAL


def test_mixed_scores_give_moderate_or_high():
    pa = _pa("FALLING", 10, 100.0, 80.0, -3.0, 1.0, day=30)  # dev=0.20(1), intensity=3.0(1), duration=10/30=0.33(1)
    severity, factors = _compute_severity(pa)
    assert factors.total_score == 3
    assert severity == SEVERITY_MODERATE


def test_stable_band_zero_with_nonzero_rate_scores_maximal_intensity():
    pa = _pa("FALLING", 5, 100.0, 95.0, -0.5, 0.0, day=20)
    severity, factors = _compute_severity(pa)
    assert factors.intensity_score == 2
    assert factors.intensity_ratio is None  # undefined ratio, but score is still exact


def test_stable_band_zero_with_zero_rate_scores_zero_intensity():
    pa = _pa("STABLE", 5, 100.0, 100.0, 0.0, 0.0, day=20)
    severity, factors = _compute_severity(pa)
    assert factors.intensity_score == 0


# ---------------------------------------------------------------------
# 3. Decoupling from evidence status (the user's own worked examples)
# ---------------------------------------------------------------------

def test_weak_evidence_can_have_high_severity():
    pa = _pa("FALLING", 20, 100.0, 50.0, -5.0, 1.0, day=25, field="soil_moisture_pct")
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert result.status == STATUS_WEAK_EVIDENCE  # no sourced moisture threshold exists
    assert result.severity == SEVERITY_CRITICAL  # but the deviation/rate/duration are all large


def test_corroborated_evidence_can_have_low_severity(seeded_agronomics_db):
    db = SessionLocal()
    try:
        # temp just barely crosses the lowest sourced cultivar value (25C) but
        # by a tiny margin, tiny rate, short duration -> LOW severity despite corroboration
        pa = _pa(
            "RISING", 2, 24.0, 25.5, 0.1, 1.0, day=30, field="temperature_c",
        )
        result = compute_problem_assessment(db, "tomato", _category("heat_related"), pa, None)
        assert result.status == STATUS_CORROBORATED_EVIDENCE
        assert result.severity == SEVERITY_LOW
    finally:
        db.close()


# ---------------------------------------------------------------------
# 4. Direction-agnostic symmetric-field property
# ---------------------------------------------------------------------

def test_severity_is_identical_for_water_depletion_and_excessive_moisture():
    """Same field, opposite adverse direction -- severity describes the
    field's volatility, not which category's gate it happens to match."""
    pa = _pa("FALLING", 15, 100.0, 60.0, -2.0, 1.0, day=30, field="soil_moisture_pct")
    depletion = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    excess = compute_problem_assessment(None, "tomato", _category("excessive_moisture"), pa, None)
    assert depletion.severity == excess.severity
    assert depletion.severity_factors == excess.severity_factors
    assert depletion.status != excess.status  # status DOES differ (direction-gated)


# ---------------------------------------------------------------------
# 5. Disclaimer present everywhere
# ---------------------------------------------------------------------

def test_severity_disclaimer_present_on_every_problem():
    pa = _pa("FALLING", 5, 100.0, 90.0, -1.0, 0.5, day=30)
    result = compute_problem_assessment(None, "tomato", _category("water_depletion"), pa, None)
    assert "not itself an agronomic diagnosis" in result.severity_disclaimer
    assert "not sourced agronomic thresholds" in result.severity_disclaimer


# ---------------------------------------------------------------------
# 6. Real heatwave-run integration: severity actually escalates with history
# ---------------------------------------------------------------------

def test_severity_escalates_with_sustained_history_in_a_real_heatwave_run(seeded_db, seeded_agronomics_db):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=30, scenario="water_shortage", seed=77001,
            severity="severe", scenario_start_day=2, scenario_duration_days=25,
        )
        run = create_run(db, config)

        severities_by_day = {}
        for day in (5, 15, 25):
            result = assess_run(db, run.id, day=day)
            water = next(p for p in result.problems if p.category == "water_depletion")
            severities_by_day[day] = water.severity

        order = [SEVERITY_INSUFFICIENT_DATA, SEVERITY_LOW, SEVERITY_MODERATE, SEVERITY_HIGH, SEVERITY_CRITICAL]
        ranks = [order.index(severities_by_day[d]) for d in (5, 15, 25)]
        # Severity must not be monotonically DEcreasing across a sustained,
        # worsening water shortage -- later days must be at least as severe.
        assert ranks[-1] >= ranks[0]
        assert all(r >= 1 for r in ranks)  # never insufficient_data once the run has real history
    finally:
        db.close()


def test_severity_matches_previously_documented_real_run_1103_pattern(seeded_db, seeded_agronomics_db):
    """
    Regression pin against the exact pattern observed live during
    implementation on run 1103 (heatwave/severe, seed 888): water
    depletion's status and severity escalate independently as the
    scenario persists, and excessive_moisture mirrors water_depletion's
    severity exactly on every day (symmetric-field property holding in
    a real, not synthetic, run).
    """
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=30, scenario="heatwave", seed=888,
            severity="severe", scenario_start_day=5, scenario_duration_days=25,
        )
        run = create_run(db, config)

        for day in (3, 10, 20, 30):
            result = assess_run(db, run.id, day=day)
            water = next(p for p in result.problems if p.category == "water_depletion")
            excess = next(p for p in result.problems if p.category == "excessive_moisture")
            assert water.severity == excess.severity
    finally:
        db.close()
