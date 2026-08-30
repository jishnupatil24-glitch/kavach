"""
Phase 6 tests: pure-function unit tests for the water/nutrient models,
farm configuration (creation/upsert), plant population hierarchy, unit
conversion, feasibility/cost, provenance tagging, integration tests
against real generated excess_irrigation/water_shortage runs, and
structural regression guards proving Phase 3/4/5 stay untouched and
unrecomputed.
"""
from __future__ import annotations

import inspect

import pytest

from app.database.session import SessionLocal
from app.services.decision_engine.seed_parameters import ensure_decision_engine_parameters
from app.services.optimization.seed_parameters import ensure_optimization_parameters
from app.services.simulator.config import build_config
from app.services.simulator.run_service import create_run


@pytest.fixture(scope="session")
def optimization_params_seeded(seeded_agronomics_db):
    """
    seed_agronomics.seed() (Phase 1, session-scoped, destructive) does
    not know about Phase 5/6's project_defined rows -- ensure both
    exist AFTER that fixture has already run, once per test session
    (Phase 6 needs Phase 5's eligibility gate to actually pass to ever
    see an ACTION_RECOMMENDED decision to optimize).
    """
    db = SessionLocal()
    try:
        ensure_decision_engine_parameters(db)
        ensure_optimization_parameters(db)
    finally:
        db.close()


# ---------------------------------------------------------------------
# 1. Unit conversion
# ---------------------------------------------------------------------

def test_area_conversion_exact_constants():
    from app.services.optimization.units import area_to_m2

    assert area_to_m2(1, "acre") == pytest.approx(4046.8564224)
    assert area_to_m2(1, "hectare") == pytest.approx(10000.0)
    assert area_to_m2(5, "m2") == pytest.approx(5.0)
    assert area_to_m2(2, "ACRE") == pytest.approx(2 * 4046.8564224)  # case-insensitive


def test_area_conversion_unknown_unit_raises():
    from app.services.optimization.units import UnsupportedAreaUnitError, area_to_m2

    with pytest.raises(UnsupportedAreaUnitError):
        area_to_m2(1, "bigha")


# ---------------------------------------------------------------------
# 2. Farm configuration: creation, upsert, validation
# ---------------------------------------------------------------------

def test_farm_configuration_creation_requires_field_area(optimization_params_seeded):
    from app.services.optimization.farm_config import upsert_farm_configuration

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=1))
        with pytest.raises(ValueError):
            upsert_farm_configuration(db, run.id)  # no field_area/field_area_unit on first create
    finally:
        db.close()


def test_farm_configuration_creation_and_upsert(optimization_params_seeded):
    from app.services.optimization.farm_config import get_farm_configuration, upsert_farm_configuration

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=2))

        created = upsert_farm_configuration(
            db, run.id, field_area=1, field_area_unit="acre", plant_population=8000,
        )
        assert created.field_area == 1
        assert created.field_area_unit == "acre"
        assert created.plant_population == 8000
        assert created.crop == "tomato"  # defaulted from the run's own crop, not guessed

        # upsert: only pump_capacity_l_per_hour changes; field_area/plant_population untouched
        updated = upsert_farm_configuration(db, run.id, pump_capacity_l_per_hour=500)
        assert updated.field_area == 1
        assert updated.plant_population == 8000
        assert updated.pump_capacity_l_per_hour == 500

        fetched = get_farm_configuration(db, run.id)
        assert fetched.pump_capacity_l_per_hour == 500

        # exactly one row, not a second inserted
        from app.models.farm_configuration import FarmConfiguration
        assert db.query(FarmConfiguration).filter(FarmConfiguration.simulation_run_id == run.id).count() == 1
    finally:
        db.close()


def test_farm_configuration_rejects_unknown_area_unit(optimization_params_seeded):
    from app.services.optimization.farm_config import upsert_farm_configuration
    from app.services.optimization.units import UnsupportedAreaUnitError

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=3))
        with pytest.raises(UnsupportedAreaUnitError):
            upsert_farm_configuration(db, run.id, field_area=1, field_area_unit="bigha")
    finally:
        db.close()


def test_farm_configuration_nonexistent_run_raises(optimization_params_seeded):
    from app.services.optimization.farm_config import RunNotFoundError, upsert_farm_configuration

    db = SessionLocal()
    try:
        with pytest.raises(RunNotFoundError):
            upsert_farm_configuration(db, 99999999, field_area=1, field_area_unit="acre")
    finally:
        db.close()


# ---------------------------------------------------------------------
# 3. Plant population hierarchy
# ---------------------------------------------------------------------

def test_plant_population_provided():
    from app.services.optimization.population import SOURCE_PROVIDED, resolve_plant_population
    from app.models.farm_configuration import FarmConfiguration

    fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)
    result = resolve_plant_population(fc)
    assert result.plants == 8000
    assert result.source == SOURCE_PROVIDED


def test_plant_population_estimated():
    from app.services.optimization.population import SOURCE_ESTIMATED, resolve_plant_population
    from app.services.optimization.units import area_to_m2
    from app.models.farm_configuration import FarmConfiguration

    fc = FarmConfiguration(
        simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre",
        plant_spacing_m=0.5, row_spacing_m=1.0,
    )
    result = resolve_plant_population(fc)
    assert result.source == SOURCE_ESTIMATED
    expected = int(area_to_m2(1, "acre") // (1.0 * 0.5))
    assert result.plants == expected


def test_plant_population_unknown_no_config():
    from app.services.optimization.population import SOURCE_UNKNOWN, resolve_plant_population

    result = resolve_plant_population(None)
    assert result.plants is None
    assert result.source == SOURCE_UNKNOWN


def test_plant_population_unknown_insufficient_data():
    from app.services.optimization.population import SOURCE_UNKNOWN, resolve_plant_population
    from app.models.farm_configuration import FarmConfiguration

    fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre")
    result = resolve_plant_population(fc)
    assert result.plants is None
    assert result.source == SOURCE_UNKNOWN


# ---------------------------------------------------------------------
# 4. Irrigation baseline by crop stage
# ---------------------------------------------------------------------

def test_irrigation_baseline_by_stage(optimization_params_seeded):
    from app.services.optimization.water_model import resolve_irrigation_baseline

    db = SessionLocal()
    try:
        initial = resolve_irrigation_baseline(db, "tomato", 10)  # kc_initial_stage: 1-26
        assert initial.value_l_per_plant_day == pytest.approx(1.5)
        assert initial.stage_name == "kc_initial_stage"

        mid = resolve_irrigation_baseline(db, "tomato", 77)  # kc_mid_stage: 63-100
        assert mid.value_l_per_plant_day == pytest.approx(3.5)

        late = resolve_irrigation_baseline(db, "tomato", 110)  # kc_late_stage: 100-120
        assert late.value_l_per_plant_day == pytest.approx(2.5)
    finally:
        db.close()


def test_irrigation_baseline_development_stage_is_interpolated(optimization_params_seeded):
    """
    kc_development_stage (DAS 27-62) has no approved baseline of its
    own -- it is covered by a deterministic linear interpolation
    between kc_initial_stage's and kc_mid_stage's approved baselines
    (FAO-56's standard crop-coefficient development-stage methodology),
    not a guessed number. Day 40: fraction=(40-27)/(62-27)=13/35 ->
    1.5 + 2.0*13/35.
    """
    from app.services.optimization.water_model import resolve_irrigation_baseline

    db = SessionLocal()
    try:
        result = resolve_irrigation_baseline(db, "tomato", 40)
        assert result.value_l_per_plant_day == pytest.approx(1.5 + 2.0 * (13 / 35))
        assert result.stage_name == "kc_development_stage"
        assert result.provenance == "PROJECT_DEFINED"
        assert "FAO-56" in result.note

        # exact boundaries: start of development == kc_initial's value, end == kc_mid's value
        start = resolve_irrigation_baseline(db, "tomato", 27)
        assert start.value_l_per_plant_day == pytest.approx(1.5)
        end = resolve_irrigation_baseline(db, "tomato", 62)
        assert end.value_l_per_plant_day == pytest.approx(3.5)
    finally:
        db.close()


def test_irrigation_baseline_no_stage_at_all_still_unavailable():
    """
    No fabrication guard, unaffected by the interpolation fix: a crop
    with no day-mapped stages at all (e.g. unseeded crop_stages for a
    fake crop) must still report UNAVAILABLE, never invent a number.
    """
    from app.services.optimization.water_model import resolve_irrigation_baseline

    db = SessionLocal()
    try:
        result = resolve_irrigation_baseline(db, "nonexistent_crop", 40)
        assert result.value_l_per_plant_day is None
    finally:
        db.close()


def test_irrigation_baseline_day100_overlap_not_silently_resolved(optimization_params_seeded):
    """
    Day 100 is the real Sharma & Changade (2025) overlap between
    kc_mid_stage (ends 100) and kc_late_stage (starts 100) -- those two
    stages have DIFFERENT approved baseline values (3.5 vs 2.5), so
    this must report UNAVAILABLE with both named, never pick one.
    """
    from app.services.optimization.water_model import resolve_irrigation_baseline

    db = SessionLocal()
    try:
        result = resolve_irrigation_baseline(db, "tomato", 100)
        assert result.value_l_per_plant_day is None
        assert "kc_mid_stage" in result.note and "kc_late_stage" in result.note
    finally:
        db.close()


# ---------------------------------------------------------------------
# 5. Severity adjustment, direction, per-plant/field-level math
# ---------------------------------------------------------------------

def test_severity_adjustment_values(optimization_params_seeded):
    from app.services.optimization import config_parameters as cfg

    db = SessionLocal()
    try:
        assert cfg.load_irrigation_adjustment_pct(db, "tomato", "LOW").value == pytest.approx(10)
        assert cfg.load_irrigation_adjustment_pct(db, "tomato", "MODERATE").value == pytest.approx(20)
        assert cfg.load_irrigation_adjustment_pct(db, "tomato", "HIGH").value == pytest.approx(30)
        assert cfg.load_irrigation_adjustment_pct(db, "tomato", "CRITICAL").value == pytest.approx(40)
    finally:
        db.close()


def test_excessive_moisture_reduces_and_water_depletion_increases(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)

        reduced = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert reduced.direction == "decrease"
        assert reduced.optimized_l_per_plant_day == pytest.approx(3.5 * 0.8)
        assert reduced.optimized_l_per_plant_day < reduced.baseline_l_per_plant_day

        increased = optimize_water(db, "tomato", 77, "water_depletion", "MODERATE", fc)
        assert increased.direction == "increase"
        assert increased.optimized_l_per_plant_day == pytest.approx(3.5 * 1.2)
        assert increased.optimized_l_per_plant_day > increased.baseline_l_per_plant_day
    finally:
        db.close()


def test_optimized_quantity_never_negative(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water

    db = SessionLocal()
    try:
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "CRITICAL", None)
        assert result.optimized_l_per_plant_day is not None
        assert result.optimized_l_per_plant_day >= 0
    finally:
        db.close()


def test_per_plant_and_field_level_calculation(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert result.baseline_l_per_day == pytest.approx(3.5 * 8000)
        assert result.optimized_l_per_day == pytest.approx(2.8 * 8000)
    finally:
        db.close()


def test_field_level_unavailable_when_population_unknown(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water

    db = SessionLocal()
    try:
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", None)
        assert result.baseline_l_per_plant_day is not None  # per-plant still reported
        assert result.baseline_l_per_day is None  # field total NOT fabricated
        assert result.optimized_l_per_day is None
        assert any("plant population is UNKNOWN" in lim for lim in result.limitations)
    finally:
        db.close()


def test_water_saved_and_saving_percentage(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert result.water_saved_l_per_day == pytest.approx(28000 - 22400)
        assert result.water_saving_percentage == pytest.approx(20.0)
    finally:
        db.close()


def test_total_water_saved_over_review_cycle(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert result.review_cycle_days == pytest.approx(3)
        assert result.total_water_saved_liters == pytest.approx(5600 * 3)
    finally:
        db.close()


# ---------------------------------------------------------------------
# 6. Irrigation efficiency precedence
# ---------------------------------------------------------------------

def test_irrigation_efficiency_precedence(optimization_params_seeded):
    from app.services.optimization import config_parameters as cfg

    db = SessionLocal()
    try:
        # 1. farmer override wins over everything
        val, source, _ = cfg.load_irrigation_efficiency_pct(db, "tomato", "drip", 99.0)
        assert (val, source) == (99.0, "farmer_override")

        # 2. system type lookup, no override
        val, source, _ = cfg.load_irrigation_efficiency_pct(db, "tomato", "sprinkler", None)
        assert (val, source) == (70.0, "system_type_lookup")

        # 3. unknown default, neither override nor recognized system
        val, source, _ = cfg.load_irrigation_efficiency_pct(db, "tomato", None, None)
        assert (val, source) == (75.0, "unknown_default")
        val, source, _ = cfg.load_irrigation_efficiency_pct(db, "tomato", "flood-irrigation-typo", None)
        assert (val, source) == (75.0, "unknown_default")
    finally:
        db.close()


# ---------------------------------------------------------------------
# 7. Resource feasibility
# ---------------------------------------------------------------------

def test_available_water_not_evaluated_when_missing():
    from app.services.optimization.feasibility import STATUS_NOT_EVALUATED, check_available_water

    check = check_available_water(None, 1000)
    assert check.status == STATUS_NOT_EVALUATED


def test_available_water_pass_and_fail_when_supplied():
    from app.services.optimization.feasibility import STATUS_FAIL, STATUS_PASS, check_available_water

    assert check_available_water(5000, 1000).status == STATUS_PASS
    assert check_available_water(500, 1000).status == STATUS_FAIL


def test_pump_capacity_not_evaluated_when_missing():
    from app.services.optimization.feasibility import STATUS_NOT_EVALUATED, check_pump_capacity

    assert check_pump_capacity(None, 1000).status == STATUS_NOT_EVALUATED


def test_pump_capacity_pass_and_fail_when_supplied():
    from app.services.optimization.feasibility import STATUS_FAIL, STATUS_PASS, check_pump_capacity

    assert check_pump_capacity(1000, 5000).status == STATUS_PASS  # 1000*24=24000 >= 5000
    assert check_pump_capacity(10, 5000).status == STATUS_FAIL  # 10*24=240 < 5000


def test_unknown_never_becomes_pass():
    from app.services.optimization.feasibility import (
        STATUS_NOT_EVALUATED, STATUS_PASS, check_available_water, check_pump_capacity,
    )

    assert check_available_water(None, None).status != STATUS_PASS
    assert check_pump_capacity(None, None).status != STATUS_PASS
    assert check_available_water(None, None).status == STATUS_NOT_EVALUATED
    assert check_pump_capacity(None, None).status == STATUS_NOT_EVALUATED


# ---------------------------------------------------------------------
# 8. N/P/K optimization
# ---------------------------------------------------------------------

def test_nitrogen_phosphorus_potassium_optimization(optimization_params_seeded):
    from app.services.optimization.nutrient_model import optimize_nutrient
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)

        n = optimize_nutrient(db, "tomato", 50, "nitrogen_related", "MODERATE", fc)
        p = optimize_nutrient(db, "tomato", 50, "phosphorus_related", "MODERATE", fc)
        k = optimize_nutrient(db, "tomato", 50, "potassium_related", "MODERATE", fc)

        for result, nutrient in ((n, "N"), (p, "P2O5"), (k, "K2O")):
            assert result.nutrient == nutrient
            assert result.baseline_g_per_plant_day is not None
            assert result.baseline_provenance == "SOURCED"
            assert result.optimized_g_per_plant_day == pytest.approx(result.baseline_g_per_plant_day * 1.2)
            assert result.optimized_provenance == "MODELED"
            assert result.total_kg_per_day is not None  # plant population known
    finally:
        db.close()


def test_nutrient_direction_always_increase_regardless_of_severity(optimization_params_seeded):
    from app.services.optimization.nutrient_model import DIRECTION_INCREASE, optimize_nutrient

    db = SessionLocal()
    try:
        for severity in ("LOW", "MODERATE", "HIGH", "CRITICAL"):
            result = optimize_nutrient(db, "tomato", 50, "nitrogen_related", severity, None)
            assert result.direction == DIRECTION_INCREASE
            assert "deficiency-only" in result.direction_basis
    finally:
        db.close()


def test_nutrient_baseline_matches_icar_reference_directly(optimization_params_seeded):
    from app.services.optimization.nutrient_model import optimize_nutrient
    from app.models.tomato_reference import TomatoReferenceProfile

    db = SessionLocal()
    try:
        row = db.query(TomatoReferenceProfile).filter(TomatoReferenceProfile.day == 50).first()
        result = optimize_nutrient(db, "tomato", 50, "nitrogen_related", "LOW", None)
        assert result.baseline_g_per_plant_day == pytest.approx(row.n_demand_g_plant_day)
    finally:
        db.close()


# ---------------------------------------------------------------------
# 9. Cost
# ---------------------------------------------------------------------

def test_cost_unavailable_without_rate():
    from app.services.optimization.cost import STATUS_UNAVAILABLE, compute_cost

    result = compute_cost(None, 100, 80, "water")
    assert result.status == STATUS_UNAVAILABLE
    assert result.baseline_cost is None


def test_cost_unavailable_without_quantity():
    from app.services.optimization.cost import STATUS_UNAVAILABLE, compute_cost

    result = compute_cost(0.001, None, None, "water")
    assert result.status == STATUS_UNAVAILABLE


def test_cost_calculation():
    from app.services.optimization.cost import STATUS_AVAILABLE, compute_cost

    result = compute_cost(0.5, 100, 80, "water")
    assert result.status == STATUS_AVAILABLE
    assert result.baseline_cost == pytest.approx(50.0)
    assert result.optimized_cost == pytest.approx(40.0)
    assert result.cost_change == pytest.approx(-10.0)


# ---------------------------------------------------------------------
# 10. Provenance and expected-outcome labeling
# ---------------------------------------------------------------------

def test_provenance_tagging_water(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert result.baseline_provenance == "PROJECT_DEFINED"
        assert result.adjustment_provenance == "PROJECT_DEFINED"
        assert result.optimized_provenance == "MODELED"
    finally:
        db.close()


def test_expected_outcome_labeling(optimization_params_seeded):
    from app.services.optimization.effectiveness import EXPECTED_OUTCOME_BASIS, expected_direction

    assert expected_direction("RISING") == "FALLING"
    assert expected_direction("FALLING") == "RISING"
    assert EXPECTED_OUTCOME_BASIS == "MODELED EXPECTED DIRECTION"

    from app.services.optimization.water_model import optimize_water
    db = SessionLocal()
    try:
        excess = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", None)
        depletion = optimize_water(db, "tomato", 77, "water_depletion", "MODERATE", None)
        assert excess.expected_direction == "FALLING"
        assert depletion.expected_direction == "RISING"
        assert excess.expected_direction_basis == EXPECTED_OUTCOME_BASIS
    finally:
        db.close()


# ---------------------------------------------------------------------
# 11. Determinism
# ---------------------------------------------------------------------

def test_deterministic_results(optimization_params_seeded):
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre", plant_population=8000)
        a = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        b = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert a == b
    finally:
        db.close()


# ---------------------------------------------------------------------
# 12. Real-run integration: excess_irrigation and water_shortage
# ---------------------------------------------------------------------

def test_real_excess_irrigation_run_first_action_day_34(optimization_params_seeded):
    """
    Same config as test_decision_engine.py's own
    test_excess_irrigation_first_action_recommended_day_34 -- day 34
    falls in kc_development_stage (27-62 DAS). Since the development-
    stage interpolation fix, this now produces a real interpolated
    baseline (fraction=(34-27)/35=0.2) instead of UNAVAILABLE.
    """
    from app.services.optimization.service import optimize_run

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)

        assessment = optimize_run(db, run.id, day=34)
        assert len(assessment.water_optimizations) == 1
        excess = assessment.water_optimizations[0]
        assert excess.category == "excessive_moisture"
        assert excess.stage_name == "kc_development_stage"
        assert excess.baseline_l_per_plant_day == pytest.approx(1.5 + 2.0 * (7 / 35))
        assert excess.baseline_provenance == "PROJECT_DEFINED"
    finally:
        db.close()


def test_real_water_shortage_run_first_action_day_35(optimization_params_seeded):
    """
    Same config as test_decision_engine.py's own
    test_water_shortage_first_action_recommended_day_35 -- day 35 also
    falls in kc_development_stage; now interpolated
    (fraction=(35-27)/35=8/35) instead of UNAVAILABLE.
    """
    from app.services.optimization.service import optimize_run

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=40, scenario="water_shortage", seed=1234,
            severity="severe", scenario_start_day=31, scenario_duration_days=8,
        )
        run = create_run(db, config)

        assessment = optimize_run(db, run.id, day=35)
        assert len(assessment.water_optimizations) == 1
        depletion = assessment.water_optimizations[0]
        assert depletion.category == "water_depletion"
        assert depletion.direction == "increase"
        assert depletion.stage_name == "kc_development_stage"
        assert depletion.baseline_l_per_plant_day == pytest.approx(1.5 + 2.0 * (8 / 35))
    finally:
        db.close()


def test_real_excess_irrigation_run_shifted_into_kc_mid_stage(optimization_params_seeded):
    """
    Same scenario/severity/seed as the canonical day-34 test, shifted
    later (scenario_start_day=70) so the action window falls inside
    kc_mid_stage (63-100 DAS) instead -- demonstrates the full
    non-UNAVAILABLE numeric chain end to end.
    """
    from app.services.optimization.service import optimize_run
    from app.services.decision_engine.history import get_stored_decision
    from app.services.optimization.farm_config import upsert_farm_configuration

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=95, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=70, scenario_duration_days=15,
        )
        run = create_run(db, config)

        first_day = None
        for day in range(70, 96):
            d = get_stored_decision(db, run.id, day=day)
            exc = next(x for x in d.decisions if x.category == "excessive_moisture")
            if exc.outcome == "ACTION_RECOMMENDED":
                first_day = day
                break
        assert first_day is not None
        assert 63 <= first_day <= 100

        upsert_farm_configuration(db, run.id, field_area=1, field_area_unit="acre", plant_population=8000)
        assessment = optimize_run(db, run.id, day=first_day)
        excess = assessment.water_optimizations[0]
        assert excess.baseline_l_per_plant_day == pytest.approx(3.5)
        assert excess.optimized_l_per_plant_day == pytest.approx(2.8)
        assert excess.baseline_l_per_day == pytest.approx(28000)
        assert excess.optimized_l_per_day == pytest.approx(22400)
        assert excess.water_saved_l_per_day == pytest.approx(5600)
        assert excess.water_saving_percentage == pytest.approx(20.0)
        assert excess.total_water_saved_liters == pytest.approx(16800)
    finally:
        db.close()


# ---------------------------------------------------------------------
# 13. Multiple simultaneous actions
# ---------------------------------------------------------------------

def test_multiple_simultaneous_actions_optimized_independently(optimization_params_seeded):
    from app.services.optimization.service import optimize_run

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)
        assessment = optimize_run(db, run.id, day=34)
        # The multi-action note is about RESOURCE-POOL interaction between
        # multiple QUANTITATIVE optimizations specifically -- a qualitative-
        # only category (e.g. heat_related, in `unsupported`) has no resource
        # quantity to interact with, so it is deliberately excluded from
        # this count.
        quantitative_actions = len(assessment.water_optimizations) + len(assessment.nutrient_optimizations)
        assert len(assessment.unsupported) >= 1  # heat_related fires alongside excessive_moisture on this run/day
        if quantitative_actions > 1:
            assert assessment.multi_action_note is not None
        else:
            assert assessment.multi_action_note is None
    finally:
        db.close()


# ---------------------------------------------------------------------
# 14. API
# ---------------------------------------------------------------------

def test_api_get_optimization(api_client, optimization_params_seeded):
    db = SessionLocal()
    try:
        config = build_config(
            duration_days=95, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=70, scenario_duration_days=15,
        )
        run = create_run(db, config)
    finally:
        db.close()

    response = api_client.get(f"/api/optimization/tomato/runs/{run.id}", params={"day": 77})
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run.id
    assert body["assessment_day"] == 77


def test_api_get_optimization_404_unknown_run(api_client):
    response = api_client.get("/api/optimization/tomato/runs/999999999")
    assert response.status_code == 404


def test_api_post_farm_config(api_client, optimization_params_seeded):
    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=999))
    finally:
        db.close()

    response = api_client.post(
        f"/api/optimization/tomato/runs/{run.id}/farm-config",
        json={"field_area": 2, "field_area_unit": "hectare", "plant_population": 5000},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["field_area"] == 2
    assert body["field_area_unit"] == "hectare"
    assert body["plant_population"] == 5000


def test_api_post_farm_config_bad_unit_422(api_client, optimization_params_seeded):
    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=5, scenario="normal", seed=998))
    finally:
        db.close()

    response = api_client.post(
        f"/api/optimization/tomato/runs/{run.id}/farm-config",
        json={"field_area": 1, "field_area_unit": "bigha"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------
# 15. Structural regression guards: Phase 5 -> Phase 6 contract
# ---------------------------------------------------------------------

def test_optimization_service_never_recomputes_or_reads_earlier_phases():
    from app.services.optimization import history as history_module
    from app.services.optimization import service as service_module

    forbidden_import_fragments = [
        "import app.models.sensor_observation",
        "from app.models.sensor_observation",
        "app.services.state_analysis.trend",
        "app.services.state_analysis.persistence",
        "app.services.state_analysis.icar_deviation",
        "app.services.state_analysis.service import analyze_run",
        "app.services.stress_assessment.service import assess_run",
        "app.services.stress_assessment.evidence",
        "decide_run",
    ]
    for module in (service_module, history_module):
        source = inspect.getsource(module)
        for fragment in forbidden_import_fragments:
            assert fragment not in source, f"{module.__name__} contains forbidden fragment: {fragment!r}"

    assert "from app.services.decision_engine.history import get_stored_decision" in inspect.getsource(service_module)


def test_no_llm_or_optimizer_vocabulary_in_optimization_modules():
    from app.services.optimization import (
        config_parameters, cost, effectiveness, farm_config, feasibility,
        nutrient_model, population, service, units, water_model,
    )

    forbidden_words = ["reinforcement", "neural", "llm", "gpt", "openai", "anthropic"]
    for module in (
        config_parameters, cost, effectiveness, farm_config, feasibility,
        nutrient_model, population, service, units, water_model,
    ):
        source = inspect.getsource(module).lower()
        for word in forbidden_words:
            assert word not in source, f"{module.__name__} contains forbidden vocabulary: {word!r}"


# ---------------------------------------------------------------------
# 16. Regression: Phase 2-5 unchanged (canonical scenario results identical)
# ---------------------------------------------------------------------

def test_phase5_canonical_scenarios_unchanged_by_phase6_addition(optimization_params_seeded):
    from app.services.decision_engine.history import get_stored_decision

    db = SessionLocal()
    try:
        config = build_config(
            duration_days=38, scenario="excess_irrigation", seed=123456,
            severity="severe", scenario_start_day=27, scenario_duration_days=9,
        )
        run = create_run(db, config)
        decision = get_stored_decision(db, run.id, day=38)
        excess = next(d for d in decision.decisions if d.category == "excessive_moisture")
        assert excess.outcome == "ACTION_RECOMMENDED"
        assert excess.status == "weak_evidence"
        assert excess.severity == "MODERATE"
        assert excess.abnormal_duration_days == 9
    finally:
        db.close()


# ---------------------------------------------------------------------
# 17. Current mode vs historical mode (day-centricity correction)
# ---------------------------------------------------------------------

def test_current_mode_uses_latest_stored_decision_not_a_new_concept(optimization_params_seeded):
    """
    "Current" means the latest persisted Phase 5 assessment for this
    run -- an ALREADY-EXISTING behavior of get_stored_decision(day=None)
    (ORDER BY day DESC), not a new concept Phase 6 invents. optimize_run
    with day=None must resolve to the exact same day.
    """
    from app.services.decision_engine.history import get_stored_decision
    from app.services.optimization.service import optimize_run

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=9, scenario="normal", seed=301))
        latest_decision = get_stored_decision(db, run.id)  # day=None -> latest, Phase 5's own behavior
        current = optimize_run(db, run.id)  # day=None -> current mode
        assert current.assessment_day == latest_decision.assessment_day == run.duration_days
    finally:
        db.close()


def test_historical_mode_uses_exact_requested_day(optimization_params_seeded):
    from app.services.optimization.service import optimize_run

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=9, scenario="normal", seed=302))
        historical = optimize_run(db, run.id, day=4)
        assert historical.assessment_day == 4
    finally:
        db.close()


def test_assessment_day_preserved_for_traceability_in_both_modes(optimization_params_seeded):
    from app.services.optimization.history import get_stored_optimization, persist_run_optimizations

    db = SessionLocal()
    try:
        run = create_run(db, build_config(duration_days=9, scenario="normal", seed=303))
        persist_run_optimizations(db, run.id)
        current = get_stored_optimization(db, run.id)
        historical = get_stored_optimization(db, run.id, day=4)
        assert current.assessment_day == 9
        assert historical.assessment_day == 4
    finally:
        db.close()


# ---------------------------------------------------------------------
# 18. Regression: feasibility/cost must not misattribute an unavailable
#     baseline to an unknown population when population IS provided
# ---------------------------------------------------------------------

def test_feasibility_and_cost_do_not_misattribute_unavailable_baseline_to_population(optimization_params_seeded):
    """
    Real bug found via `python -m app.optimization_cli --run-id 584 --day 40`:
    the CLI showed "Plant Population: 8,000 / PROVIDED" but feasibility/
    cost said "plant population UNKNOWN". Root cause: feasibility.py/
    cost.py hardcoded that explanation for ANY None quantity, regardless
    of true cause. Day 100 (the real Kc kc_mid_stage/kc_late_stage
    overlap, genuinely UNAVAILABLE) reproduces the same shape with a
    fully PROVIDED population and must no longer say "population" at all.
    """
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(
            simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre",
            plant_population=8000, irrigation_system_type="drip",
            available_water_l_per_day=50000, pump_capacity_l_per_hour=3000,
            water_cost_per_liter=0.0005,
        )
        result = optimize_water(db, "tomato", 100, "excessive_moisture", "MODERATE", fc)

        assert result.plant_population.plants == 8000
        assert result.plant_population.source == "PROVIDED"
        assert result.baseline_l_per_plant_day is None  # genuinely unavailable: stage overlap, not population

        for check in result.feasibility:
            assert check.status == "NOT_EVALUATED"
            assert "population" not in check.detail.lower()

        assert result.cost.status == "UNAVAILABLE"
        assert "population" not in result.cost.detail.lower()
    finally:
        db.close()


def test_feasibility_and_cost_still_correctly_blame_population_when_it_is_the_real_cause(optimization_params_seeded):
    """
    The fix must not overcorrect: when population genuinely IS unknown
    (and available_water/pump_capacity/cost ARE configured, and the
    day/stage baseline IS available), the message should still name
    population as the cause -- only the misattribution (blaming
    population when it ISN'T the cause) was the bug.
    """
    from app.services.optimization.water_model import optimize_water
    from app.models.farm_configuration import FarmConfiguration

    db = SessionLocal()
    try:
        fc = FarmConfiguration(
            simulation_run_id=1, crop="tomato", field_area=1, field_area_unit="acre",
            available_water_l_per_day=50000, pump_capacity_l_per_hour=3000,
            water_cost_per_liter=0.0005,
        )  # no plant_population, no spacing -> UNKNOWN
        result = optimize_water(db, "tomato", 77, "excessive_moisture", "MODERATE", fc)
        assert result.baseline_l_per_plant_day is not None  # kc_mid_stage, available
        assert result.plant_population.plants is None
        for check in result.feasibility:
            assert check.status == "NOT_EVALUATED"
            assert "population" in check.detail.lower()
        assert "population" in result.cost.detail.lower()
    finally:
        db.close()
