"""
Quantitative irrigation optimization for water_depletion (increase) and
excessive_moisture (decrease). Baseline is a PROJECT_DEFINED prototype
per-stage crop water requirement (L/plant/day, theoretical -- NOT a
delivered/irrigation-system volume); optimized is MODELED (baseline
adjusted by a severity-keyed PROJECT_DEFINED percentage). Direction
comes from the category, never from severity -- severity only sets
magnitude.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.farm_configuration import FarmConfiguration
from app.services.optimization import config_parameters as cfg
from app.services.optimization import cost as cost_mod
from app.services.optimization import feasibility as feasibility_mod
from app.services.optimization.effectiveness import EXPECTED_OUTCOME_BASIS, expected_direction
from app.services.optimization.population import PlantPopulationResult, resolve_plant_population
from app.services.state_analysis.crop_stage_context import resolve_crop_stages
from app.services.stress_assessment.categories import CATEGORIES

PROVENANCE_SOURCED = "SOURCED"
PROVENANCE_PROJECT_DEFINED = "PROJECT_DEFINED"
PROVENANCE_MODELED = "MODELED"

WATER_CATEGORIES = ("water_depletion", "excessive_moisture")

_ADVERSE_TREND_BY_CATEGORY = {c.key: c.adverse_trend for c in CATEGORIES}
_ACTION_LABEL_BY_CATEGORY = {c.key: c.label for c in CATEGORIES}


@dataclass(frozen=True)
class BaselineResolution:
    value_l_per_plant_day: float | None
    stage_name: str | None
    provenance: str
    note: str


_DEVELOPMENT_STAGE_NAME = "kc_development_stage"


def _interpolate_development_stage_baseline(
    db: Session, crop: str, day: int, stage_name: str, start_day: int, end_day: int,
) -> BaselineResolution:
    """
    kc_development_stage (Sharma & Changade 2025's own DAS 27-62 window)
    sits between kc_initial_stage and kc_mid_stage with no approved
    baseline of its own. FAO-56 (Allen et al. 1998 -- already cited in
    this project's agronomic_sources for ETo/root-zone-depth) defines
    exactly this situation: the "development stage" of the standard
    4-stage crop-coefficient curve is not a separate fixed value, it is
    the LINEAR RAMP between the initial and mid-season values. Applying
    that real, citable methodology to KAVACH's own two already-approved
    endpoint baselines is the smallest deterministic, non-fabricated way
    to cover this window -- it introduces no new numeric assumption, only
    a documented interpolation RULE between two numbers already approved.

    The two endpoint VALUES remain PROJECT_DEFINED prototypes (not
    derived from a real Kc x ETo chain -- see seed_parameters.py), so the
    interpolated result is PROJECT_DEFINED too, never SOURCED. FAO-56 is
    cited here as the basis for the INTERPOLATION METHOD only, not as the
    source of the numeric endpoints.
    """
    initial = cfg.load_irrigation_baseline_for_stage(db, crop, "kc_initial_stage")
    mid = cfg.load_irrigation_baseline_for_stage(db, crop, "kc_mid_stage")
    if initial.value is None or mid.value is None:
        return BaselineResolution(
            None, stage_name, PROVENANCE_PROJECT_DEFINED,
            "kc_development_stage interpolation requires both kc_initial_stage and kc_mid_stage "
            "baselines, and at least one is missing -- run "
            "`python -m app.services.optimization.seed_parameters` first.",
        )

    span = end_day - start_day
    fraction = 0.0 if span <= 0 else (day - start_day) / span
    fraction = max(0.0, min(1.0, fraction))
    value = initial.value + (mid.value - initial.value) * fraction

    return BaselineResolution(
        value, stage_name, PROVENANCE_PROJECT_DEFINED,
        f"PROJECT_DEFINED linear interpolation across kc_development_stage (day "
        f"{start_day}-{end_day}), from kc_initial_stage's baseline ({initial.value} L/plant/day) "
        f"to kc_mid_stage's baseline ({mid.value} L/plant/day). Interpolation METHOD is grounded in "
        "FAO-56's standard crop-coefficient development-stage methodology (Allen et al. 1998, already "
        "cited in this project's agronomic_sources); the two endpoint VALUES remain KAVACH's own "
        "project-defined prototypes, not a sourced Kc x ETo chain. Result is PROJECT_DEFINED, not SOURCED.",
    )


def resolve_irrigation_baseline(db: Session, crop: str, day: int) -> BaselineResolution:
    stages = resolve_crop_stages(db, crop, day)
    matched = [s for s in stages if s.name in cfg.BASELINE_IRRIGATION_PARAM_BY_STAGE_NAME]

    if not matched:
        development = next((s for s in stages if s.name == _DEVELOPMENT_STAGE_NAME), None)
        if development is not None:
            return _interpolate_development_stage_baseline(
                db, crop, day, development.name, development.start_day, development.end_day,
            )

        seen = [s.name for s in stages] or ["no day-mapped stage"]
        return BaselineResolution(
            None, None, PROVENANCE_PROJECT_DEFINED,
            f"Day {day} resolves to stage(s) {seen} -- no approved baseline_irrigation parameter "
            "and no interpolation rule covers this window. Baseline UNAVAILABLE, not guessed.",
        )

    values: dict[str, float] = {}
    for s in matched:
        result = cfg.load_irrigation_baseline_for_stage(db, crop, s.name)
        if result.value is not None:
            values[s.name] = result.value

    if not values:
        return BaselineResolution(
            None, matched[0].name, PROVENANCE_PROJECT_DEFINED,
            f"Matched stage {matched[0].name!r} has no seeded baseline_irrigation parameter -- "
            "run `python -m app.services.optimization.seed_parameters` first.",
        )

    unique_values = set(values.values())
    if len(unique_values) > 1:
        return BaselineResolution(
            None, "/".join(values), PROVENANCE_PROJECT_DEFINED,
            f"Day {day} overlaps stages {list(values)} with DIFFERENT baseline values {values} -- "
            "not silently resolved to one (mirrors Phase 3/4's own day-100 overlap handling).",
        )

    stage_name = next(iter(values))
    return BaselineResolution(
        next(iter(unique_values)), stage_name, PROVENANCE_PROJECT_DEFINED,
        f"PROJECT_DEFINED prototype baseline for {stage_name}.",
    )


@dataclass(frozen=True)
class WaterOptimization:
    category: str
    action_label: str
    direction: str  # "increase" | "decrease"

    stage_name: str | None
    baseline_l_per_plant_day: float | None
    baseline_provenance: str

    severity: str
    adjustment_pct: float | None
    adjustment_provenance: str

    optimized_l_per_plant_day: float | None
    optimized_provenance: str

    typical_l_per_plant_day: float | None
    typical_provenance: str
    typical_application_multiplier_pct: float | None

    plant_population: PlantPopulationResult
    baseline_l_per_day: float | None
    optimized_l_per_day: float | None
    typical_l_per_day: float | None
    water_saved_l_per_day: float | None
    water_saving_percentage: float | None
    water_saved_vs_typical_l_per_day: float | None
    water_saved_vs_typical_percentage: float | None

    review_cycle_days: float | None
    review_cycle_provenance: str
    total_baseline_liters: float | None
    total_optimized_liters: float | None
    total_water_saved_liters: float | None
    total_typical_liters: float | None
    total_water_saved_vs_typical_liters: float | None

    irrigation_efficiency_pct: float | None
    irrigation_efficiency_source: str
    delivered_baseline_l_per_day: float | None
    delivered_optimized_l_per_day: float | None

    feasibility: list[feasibility_mod.FeasibilityCheck]
    cost: cost_mod.CostResult

    expected_direction: str | None
    expected_direction_basis: str

    limitations: list[str] = field(default_factory=list)


def optimize_water(
    db: Session, crop: str, day: int, category: str, severity: str,
    farm_config: FarmConfiguration | None,
) -> WaterOptimization:
    limitations: list[str] = []

    baseline = resolve_irrigation_baseline(db, crop, day)
    if baseline.value_l_per_plant_day is None:
        limitations.append(baseline.note)

    adjustment = cfg.load_irrigation_adjustment_pct(db, crop, severity)
    if adjustment.value is None:
        limitations.append(adjustment.note)

    direction = "increase" if category == "water_depletion" else "decrease"

    optimized_l_per_plant_day = None
    if baseline.value_l_per_plant_day is not None and adjustment.value is not None:
        factor = (1 + adjustment.value / 100) if direction == "increase" else (1 - adjustment.value / 100)
        optimized_l_per_plant_day = max(0.0, baseline.value_l_per_plant_day * factor)

    typical_multiplier = cfg.load_typical_application_multiplier_pct(db, crop)
    if typical_multiplier.value is None:
        limitations.append(typical_multiplier.note)

    typical_l_per_plant_day = None
    if baseline.value_l_per_plant_day is not None and typical_multiplier.value is not None:
        typical_l_per_plant_day = baseline.value_l_per_plant_day * (1 + typical_multiplier.value / 100)

    population = resolve_plant_population(farm_config)

    baseline_l_per_day = optimized_l_per_day = typical_l_per_day = None
    water_saved_l_per_day = water_saving_percentage = None
    water_saved_vs_typical_l_per_day = water_saved_vs_typical_percentage = None
    if population.plants is not None:
        if baseline.value_l_per_plant_day is not None:
            baseline_l_per_day = baseline.value_l_per_plant_day * population.plants
        if optimized_l_per_plant_day is not None:
            optimized_l_per_day = optimized_l_per_plant_day * population.plants
        if typical_l_per_plant_day is not None:
            typical_l_per_day = typical_l_per_plant_day * population.plants
        if baseline_l_per_day is not None and optimized_l_per_day is not None:
            water_saved_l_per_day = baseline_l_per_day - optimized_l_per_day
            if baseline_l_per_day > 0:
                water_saving_percentage = water_saved_l_per_day / baseline_l_per_day * 100
        if typical_l_per_day is not None and optimized_l_per_day is not None:
            # Positive = typical > KAVACH (a real saving vs. typical application).
            # Negative = KAVACH > typical (KAVACH needs MORE than typical application --
            # the frontend must render this as "additional water required", never a saving).
            water_saved_vs_typical_l_per_day = typical_l_per_day - optimized_l_per_day
            if typical_l_per_day > 0:
                water_saved_vs_typical_percentage = water_saved_vs_typical_l_per_day / typical_l_per_day * 100
    else:
        limitations.append("Field-total water quantities UNAVAILABLE -- plant population is UNKNOWN.")

    review_cycle = cfg.load_review_cycle_days(db, crop)
    if review_cycle.value is None:
        limitations.append(review_cycle.note)

    total_baseline_liters = total_optimized_liters = total_water_saved_liters = None
    total_typical_liters = total_water_saved_vs_typical_liters = None
    if review_cycle.value is not None:
        if baseline_l_per_day is not None:
            total_baseline_liters = baseline_l_per_day * review_cycle.value
        if optimized_l_per_day is not None:
            total_optimized_liters = optimized_l_per_day * review_cycle.value
        if total_baseline_liters is not None and total_optimized_liters is not None:
            total_water_saved_liters = total_baseline_liters - total_optimized_liters
        if typical_l_per_day is not None:
            total_typical_liters = typical_l_per_day * review_cycle.value
        if water_saved_vs_typical_l_per_day is not None:
            total_water_saved_vs_typical_liters = water_saved_vs_typical_l_per_day * review_cycle.value

    efficiency_pct, efficiency_source, efficiency_note = cfg.load_irrigation_efficiency_pct(
        db, crop,
        farm_config.irrigation_system_type if farm_config else None,
        farm_config.irrigation_efficiency_pct if farm_config else None,
    )
    limitations.append(efficiency_note)

    delivered_baseline_l_per_day = delivered_optimized_l_per_day = None
    if efficiency_pct is not None and efficiency_pct > 0:
        if baseline_l_per_day is not None:
            delivered_baseline_l_per_day = baseline_l_per_day / (efficiency_pct / 100)
        if optimized_l_per_day is not None:
            delivered_optimized_l_per_day = optimized_l_per_day / (efficiency_pct / 100)

    # The TRUE reason delivered_optimized_l_per_day can be None is not
    # always "population unknown" -- diagnose the actual cause so
    # feasibility/cost don't misreport it (this was a real bug: a run
    # with a fully PROVIDED population showed "plant population UNKNOWN"
    # here, when the real cause was the baseline being unavailable for
    # this day's crop stage).
    volume_unavailable_reason = None
    if delivered_optimized_l_per_day is None:
        if population.plants is None:
            volume_unavailable_reason = (
                "Required delivered field volume is unavailable -- plant population is UNKNOWN."
            )
        elif optimized_l_per_day is None:
            volume_unavailable_reason = (
                "Required delivered field volume is unavailable because the optimized quantity "
                "could not be calculated for this day (see BASELINE/OPTIMIZED PLAN above)."
            )
        elif efficiency_pct is None:
            volume_unavailable_reason = (
                "Required delivered field volume is unavailable because irrigation efficiency "
                "could not be determined."
            )

    feasibility_checks = [
        feasibility_mod.check_available_water(
            farm_config.available_water_l_per_day if farm_config else None,
            delivered_optimized_l_per_day, unavailable_reason=volume_unavailable_reason,
        ),
        feasibility_mod.check_pump_capacity(
            farm_config.pump_capacity_l_per_hour if farm_config else None,
            delivered_optimized_l_per_day, unavailable_reason=volume_unavailable_reason,
        ),
    ]

    cost_result = cost_mod.compute_cost(
        farm_config.water_cost_per_liter if farm_config else None,
        delivered_baseline_l_per_day, delivered_optimized_l_per_day, "water",
        unavailable_reason=volume_unavailable_reason,
    )

    direction_label = expected_direction(_ADVERSE_TREND_BY_CATEGORY[category])

    return WaterOptimization(
        category=category,
        action_label=_ACTION_LABEL_BY_CATEGORY[category],
        direction=direction,
        stage_name=baseline.stage_name,
        baseline_l_per_plant_day=baseline.value_l_per_plant_day,
        baseline_provenance=PROVENANCE_PROJECT_DEFINED,
        severity=severity,
        adjustment_pct=adjustment.value,
        adjustment_provenance=PROVENANCE_PROJECT_DEFINED,
        optimized_l_per_plant_day=optimized_l_per_plant_day,
        optimized_provenance=PROVENANCE_MODELED,
        typical_l_per_plant_day=typical_l_per_plant_day,
        typical_provenance=PROVENANCE_PROJECT_DEFINED,
        typical_application_multiplier_pct=typical_multiplier.value,
        plant_population=population,
        baseline_l_per_day=baseline_l_per_day,
        optimized_l_per_day=optimized_l_per_day,
        typical_l_per_day=typical_l_per_day,
        water_saved_l_per_day=water_saved_l_per_day,
        water_saving_percentage=water_saving_percentage,
        water_saved_vs_typical_l_per_day=water_saved_vs_typical_l_per_day,
        water_saved_vs_typical_percentage=water_saved_vs_typical_percentage,
        review_cycle_days=review_cycle.value,
        review_cycle_provenance=PROVENANCE_PROJECT_DEFINED,
        total_baseline_liters=total_baseline_liters,
        total_optimized_liters=total_optimized_liters,
        total_water_saved_liters=total_water_saved_liters,
        total_typical_liters=total_typical_liters,
        total_water_saved_vs_typical_liters=total_water_saved_vs_typical_liters,
        irrigation_efficiency_pct=efficiency_pct,
        irrigation_efficiency_source=efficiency_source,
        delivered_baseline_l_per_day=delivered_baseline_l_per_day,
        delivered_optimized_l_per_day=delivered_optimized_l_per_day,
        feasibility=feasibility_checks,
        cost=cost_result,
        expected_direction=direction_label,
        expected_direction_basis=EXPECTED_OUTCOME_BASIS,
        limitations=limitations,
    )
