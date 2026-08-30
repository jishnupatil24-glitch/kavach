"""
Quantitative N/P/K optimization. Baseline is the SOURCED ICAR per-plant-
per-day nutrient demand (tomato_reference_profile, Phase 0) -- NOT a
new project-defined value. Direction is ALWAYS "increase", derived from
the category definition (nitrogen_related/phosphorus_related/
potassium_related are deficiency-only -- Phase 4's own categories.py
has no "excess_*" counterpart for any of the three, confirmed by
repository audit), never from severity. Severity only sets the
PROJECT_DEFINED adjustment magnitude.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models.farm_configuration import FarmConfiguration
from app.models.tomato_reference import TomatoReferenceProfile
from app.services.optimization import config_parameters as cfg
from app.services.optimization import cost as cost_mod
from app.services.optimization.effectiveness import EXPECTED_OUTCOME_BASIS, expected_direction
from app.services.optimization.population import PlantPopulationResult, resolve_plant_population
from app.services.stress_assessment.categories import CATEGORIES

PROVENANCE_SOURCED = "SOURCED"
PROVENANCE_PROJECT_DEFINED = "PROJECT_DEFINED"
PROVENANCE_MODELED = "MODELED"

NUTRIENT_CATEGORIES = ("nitrogen_related", "phosphorus_related", "potassium_related")

_ADVERSE_TREND_BY_CATEGORY = {c.key: c.adverse_trend for c in CATEGORIES}
_ACTION_LABEL_BY_CATEGORY = {c.key: c.label for c in CATEGORIES}

_NUTRIENT_LABEL = {"nitrogen_related": "N", "phosphorus_related": "P2O5", "potassium_related": "K2O"}
_BASELINE_FIELD = {
    "nitrogen_related": "n_demand_g_plant_day",
    "phosphorus_related": "p2o5_demand_g_plant_day",
    "potassium_related": "k2o_demand_g_plant_day",
}
_COST_FIELD = {
    "nitrogen_related": "fertilizer_cost_per_kg_n",
    "phosphorus_related": "fertilizer_cost_per_kg_p2o5",
    "potassium_related": "fertilizer_cost_per_kg_k2o",
}

DIRECTION_INCREASE = "increase"
DIRECTION_BASIS = (
    "Category is deficiency-only (Phase 4's categories.py defines no 'excess_*' counterpart "
    "for this nutrient) -- direction is fixed by the category definition itself, never by severity."
)


@dataclass(frozen=True)
class NutrientOptimization:
    category: str
    nutrient: str  # N | P2O5 | K2O
    action_label: str
    direction: str  # always "increase"
    direction_basis: str

    baseline_g_per_plant_day: float | None
    baseline_provenance: str

    severity: str
    adjustment_pct: float | None
    adjustment_provenance: str

    optimized_g_per_plant_day: float | None
    optimized_provenance: str

    plant_population: PlantPopulationResult
    total_g_per_day: float | None
    total_kg_per_day: float | None
    baseline_total_kg_per_day: float | None

    duration_days: float | None
    duration_provenance: str
    total_quantity_kg: float | None
    baseline_total_quantity_kg: float | None

    cost: cost_mod.CostResult

    expected_direction: str | None
    expected_direction_basis: str

    limitations: list[str] = field(default_factory=list)


def _load_icar_demand(db: Session, day: int, field_name: str) -> float | None:
    """
    Reads Phase 0's own frozen ICAR reference row directly for its
    per-plant-per-day demand columns -- NOT exposed by
    app.services.simulator.baseline.load_baseline (Phase 2's loader,
    scoped to what the simulator generates; demand is intentionally
    never simulated). Read-only, same table Phase 3's icar_deviation.py
    already reuses via that loader for its OTHER columns.
    """
    row = db.query(TomatoReferenceProfile).filter(TomatoReferenceProfile.day == day).first()
    if row is None:
        return None
    return getattr(row, field_name)


def optimize_nutrient(
    db: Session, crop: str, day: int, category: str, severity: str,
    farm_config: FarmConfiguration | None,
) -> NutrientOptimization:
    limitations: list[str] = []

    baseline_g_per_plant_day = _load_icar_demand(db, day, _BASELINE_FIELD[category])
    if baseline_g_per_plant_day is None:
        limitations.append(
            f"No ICAR reference row exists for day {day} (reference covers day 1-120 only) -- "
            "baseline UNAVAILABLE."
        )

    adjustment = cfg.load_nutrient_adjustment_pct(db, crop, severity)
    if adjustment.value is None:
        limitations.append(adjustment.note)

    optimized_g_per_plant_day = None
    if baseline_g_per_plant_day is not None and adjustment.value is not None:
        optimized_g_per_plant_day = max(0.0, baseline_g_per_plant_day * (1 + adjustment.value / 100))

    population = resolve_plant_population(farm_config)

    total_g_per_day = total_kg_per_day = baseline_total_kg_per_day = None
    if population.plants is not None:
        if optimized_g_per_plant_day is not None:
            total_g_per_day = optimized_g_per_plant_day * population.plants
            total_kg_per_day = total_g_per_day / 1000
        if baseline_g_per_plant_day is not None:
            baseline_total_kg_per_day = (baseline_g_per_plant_day * population.plants) / 1000
    else:
        limitations.append("Field-total nutrient quantities UNAVAILABLE -- plant population is UNKNOWN.")

    review_cycle = cfg.load_review_cycle_days(db, crop)
    if review_cycle.value is None:
        limitations.append(review_cycle.note)

    total_quantity_kg = baseline_total_quantity_kg = None
    if review_cycle.value is not None:
        if total_kg_per_day is not None:
            total_quantity_kg = total_kg_per_day * review_cycle.value
        if baseline_total_kg_per_day is not None:
            baseline_total_quantity_kg = baseline_total_kg_per_day * review_cycle.value

    quantity_unavailable_reason = None
    if total_quantity_kg is None or baseline_total_quantity_kg is None:
        if population.plants is None:
            quantity_unavailable_reason = (
                f"Field-level {_NUTRIENT_LABEL[category]} quantity is unavailable -- plant "
                "population is UNKNOWN."
            )
        elif baseline_g_per_plant_day is None:
            quantity_unavailable_reason = (
                "Field-level quantity is unavailable because no ICAR baseline exists for this day."
            )
        elif review_cycle.value is None:
            quantity_unavailable_reason = (
                "Field-level quantity is unavailable because the review cycle duration could not "
                "be determined."
            )

    unit_cost = getattr(farm_config, _COST_FIELD[category], None) if farm_config else None
    cost_result = cost_mod.compute_cost(
        unit_cost, baseline_total_quantity_kg, total_quantity_kg, _NUTRIENT_LABEL[category],
        unavailable_reason=quantity_unavailable_reason,
    )

    direction_label = expected_direction(_ADVERSE_TREND_BY_CATEGORY[category])

    return NutrientOptimization(
        category=category,
        nutrient=_NUTRIENT_LABEL[category],
        action_label=_ACTION_LABEL_BY_CATEGORY[category],
        direction=DIRECTION_INCREASE,
        direction_basis=DIRECTION_BASIS,
        baseline_g_per_plant_day=baseline_g_per_plant_day,
        baseline_provenance=PROVENANCE_SOURCED,
        severity=severity,
        adjustment_pct=adjustment.value,
        adjustment_provenance=PROVENANCE_PROJECT_DEFINED,
        optimized_g_per_plant_day=optimized_g_per_plant_day,
        optimized_provenance=PROVENANCE_MODELED,
        plant_population=population,
        total_g_per_day=total_g_per_day,
        total_kg_per_day=total_kg_per_day,
        baseline_total_kg_per_day=baseline_total_kg_per_day,
        duration_days=review_cycle.value,
        duration_provenance=PROVENANCE_PROJECT_DEFINED,
        total_quantity_kg=total_quantity_kg,
        baseline_total_quantity_kg=baseline_total_quantity_kg,
        cost=cost_result,
        expected_direction=direction_label,
        expected_direction_basis=EXPECTED_OUTCOME_BASIS,
        limitations=limitations,
    )
