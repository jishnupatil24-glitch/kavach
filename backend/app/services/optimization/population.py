"""
Plant population resolution -- approved hierarchy, never a silent
assumption. PROVIDED > ESTIMATED > UNKNOWN, in that order.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.farm_configuration import FarmConfiguration
from app.services.optimization.units import area_to_m2

SOURCE_PROVIDED = "PROVIDED"
SOURCE_ESTIMATED = "ESTIMATED"
SOURCE_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PlantPopulationResult:
    plants: int | None
    source: str  # PROVIDED | ESTIMATED | UNKNOWN
    note: str


def resolve_plant_population(farm_config: FarmConfiguration | None) -> PlantPopulationResult:
    if farm_config is None:
        return PlantPopulationResult(
            None, SOURCE_UNKNOWN, "No farm configuration exists for this run -- plant population is unknown."
        )

    if farm_config.plant_population is not None:
        return PlantPopulationResult(
            farm_config.plant_population, SOURCE_PROVIDED,
            "Explicit plant_population from farm configuration.",
        )

    if (
        farm_config.plant_spacing_m is not None and farm_config.plant_spacing_m > 0
        and farm_config.row_spacing_m is not None and farm_config.row_spacing_m > 0
    ):
        area_m2 = area_to_m2(farm_config.field_area, farm_config.field_area_unit)
        plants = int(area_m2 // (farm_config.row_spacing_m * farm_config.plant_spacing_m))
        return PlantPopulationResult(
            plants, SOURCE_ESTIMATED,
            f"Estimated from field_area ({farm_config.field_area} {farm_config.field_area_unit} = "
            f"{area_m2:.1f} m2) / (row_spacing_m x plant_spacing_m = "
            f"{farm_config.row_spacing_m} x {farm_config.plant_spacing_m} m2).",
        )

    return PlantPopulationResult(
        None, SOURCE_UNKNOWN,
        "plant_population not provided, and field_area/row_spacing_m/plant_spacing_m are "
        "insufficient to estimate one -- not silently assumed.",
    )
