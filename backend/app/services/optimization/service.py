"""
Phase 6 orchestrator. `optimize_run()` is the single entrypoint both
the CLI (via stored history) and the API (on-demand) ultimately rely
on -- neither may duplicate the quantity math in this module or its
sibling modules.

Consumes ONLY: app.services.decision_engine.history.get_stored_decision
(Phase 5's OWN STORED history -- never Phase 5's live on-demand
compute entrypoint, which would mean Phase 6 depending on Phase 5
recomputing anything). Never imports
Phase 3/4 calculation modules, never queries sensor_observations or
state_analysis_history/problem_assessment_history directly. This is
the same hard boundary every earlier phase already enforces.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.services.decision_engine.history import get_stored_decision
from app.services.decision_engine.service import InvalidDayError, RunNotFoundError, StateAnalysisError
from app.services.decision_engine.validation import OUTCOME_ACTION_RECOMMENDED
from app.services.optimization.farm_config import get_farm_configuration
from app.services.optimization.nutrient_model import NUTRIENT_CATEGORIES, NutrientOptimization, optimize_nutrient
from app.services.optimization.water_model import WATER_CATEGORIES, WaterOptimization, optimize_water

__all__ = [
    "StateAnalysisError", "RunNotFoundError", "InvalidDayError",
    "OptimizationAssessment", "optimize_run",
]

MULTIPLE_ACTIONS_NOTE = (
    "Water and nutrient actions are optimized independently as separate resource pools "
    "(liters vs. kilograms) -- Phase 5 already prevents opposite-direction irrigation "
    "conflicts (water_depletion/excessive_moisture is one of its own CONFLICT_PAIRS, so "
    "both never reach ACTION_RECOMMENDED simultaneously). Fertigation coupling (nutrients "
    "delivered via irrigation water) is a real-world interaction NOT modeled here."
)

GLOBAL_LIMITATIONS = [
    "Prototype optimization model.",
    "Values marked PROJECT_DEFINED are assumptions and are not scientifically validated "
    "agronomic prescriptions.",
]


@dataclass(frozen=True)
class FarmConfigSnapshot:
    exists: bool
    crop: str | None = None
    field_area: float | None = None
    field_area_unit: str | None = None
    plant_population: int | None = None
    plant_spacing_m: float | None = None
    row_spacing_m: float | None = None
    cultivar: str | None = None
    irrigation_system_type: str | None = None
    irrigation_efficiency_pct: float | None = None
    available_water_l_per_day: float | None = None
    pump_capacity_l_per_hour: float | None = None
    pump_power_kw: float | None = None
    water_cost_per_liter: float | None = None
    fertilizer_cost_per_kg_n: float | None = None
    fertilizer_cost_per_kg_p2o5: float | None = None
    fertilizer_cost_per_kg_k2o: float | None = None


def _snapshot_farm_config(farm_config) -> FarmConfigSnapshot:
    if farm_config is None:
        return FarmConfigSnapshot(exists=False)
    return FarmConfigSnapshot(
        exists=True,
        crop=farm_config.crop,
        field_area=farm_config.field_area,
        field_area_unit=farm_config.field_area_unit,
        plant_population=farm_config.plant_population,
        plant_spacing_m=farm_config.plant_spacing_m,
        row_spacing_m=farm_config.row_spacing_m,
        cultivar=farm_config.cultivar,
        irrigation_system_type=farm_config.irrigation_system_type,
        irrigation_efficiency_pct=farm_config.irrigation_efficiency_pct,
        available_water_l_per_day=farm_config.available_water_l_per_day,
        pump_capacity_l_per_hour=farm_config.pump_capacity_l_per_hour,
        pump_power_kw=farm_config.pump_power_kw,
        water_cost_per_liter=farm_config.water_cost_per_liter,
        fertilizer_cost_per_kg_n=farm_config.fertilizer_cost_per_kg_n,
        fertilizer_cost_per_kg_p2o5=farm_config.fertilizer_cost_per_kg_p2o5,
        fertilizer_cost_per_kg_k2o=farm_config.fertilizer_cost_per_kg_k2o,
    )


@dataclass(frozen=True)
class UnsupportedCategoryNote:
    category: str
    action_label: str | None
    reason: str


@dataclass(frozen=True)
class OptimizationAssessment:
    run_id: int
    crop: str
    assessment_day: int
    farm_configuration: FarmConfigSnapshot
    water_optimizations: list[WaterOptimization] = field(default_factory=list)
    nutrient_optimizations: list[NutrientOptimization] = field(default_factory=list)
    unsupported: list[UnsupportedCategoryNote] = field(default_factory=list)
    multi_action_note: str | None = None
    limitations: list[str] = field(default_factory=list)


def optimize_run(db: Session, run_id: int, day: int | None = None) -> OptimizationAssessment:
    decision = get_stored_decision(db, run_id, day=day)
    if decision is None:
        raise InvalidDayError(
            f"No persisted Phase 5 decision found for simulation run {run_id}"
            + (f" at day {day}" if day is not None else "")
            + " -- Phase 6 cannot optimize a run that has no Phase 5 history yet."
        )

    farm_config = get_farm_configuration(db, run_id)
    recommended = [d for d in decision.decisions if d.outcome == OUTCOME_ACTION_RECOMMENDED]
    recommended.sort(key=lambda d: (d.priority if d.priority is not None else 10_000))

    water_optimizations: list[WaterOptimization] = []
    nutrient_optimizations: list[NutrientOptimization] = []
    unsupported: list[UnsupportedCategoryNote] = []

    for d in recommended:
        if d.category in WATER_CATEGORIES:
            water_optimizations.append(
                optimize_water(db, decision.crop, decision.assessment_day, d.category, d.severity, farm_config)
            )
        elif d.category in NUTRIENT_CATEGORIES:
            nutrient_optimizations.append(
                optimize_nutrient(db, decision.crop, decision.assessment_day, d.category, d.severity, farm_config)
            )
        else:
            unsupported.append(
                UnsupportedCategoryNote(
                    category=d.category, action_label=d.action_label,
                    reason=(
                        "No quantitative resource model exists for this category -- it would require "
                        "equipment-specific parameters (fan/misting/lamp capacity) not in the approved "
                        "farmer-input list. Recommendation stays qualitative, unchanged from Phase 5."
                    ),
                )
            )

    multi_action_note = MULTIPLE_ACTIONS_NOTE if (len(water_optimizations) + len(nutrient_optimizations)) > 1 else None

    return OptimizationAssessment(
        run_id=run_id,
        crop=decision.crop,
        assessment_day=decision.assessment_day,
        farm_configuration=_snapshot_farm_config(farm_config),
        water_optimizations=water_optimizations,
        nutrient_optimizations=nutrient_optimizations,
        unsupported=unsupported,
        multi_action_note=multi_action_note,
        limitations=list(GLOBAL_LIMITATIONS),
    )
