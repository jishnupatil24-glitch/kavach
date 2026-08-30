from pydantic import BaseModel, ConfigDict


class PlantPopulationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    plants: int | None
    source: str
    note: str


class FeasibilityCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    status: str
    detail: str


class CostResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str
    baseline_cost: float | None
    optimized_cost: float | None
    cost_change: float | None
    detail: str


class WaterOptimizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    action_label: str
    direction: str
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
    plant_population: PlantPopulationOut
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
    feasibility: list[FeasibilityCheckOut]
    cost: CostResultOut
    expected_direction: str | None
    expected_direction_basis: str
    limitations: list[str]


class NutrientOptimizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    nutrient: str
    action_label: str
    direction: str
    direction_basis: str
    baseline_g_per_plant_day: float | None
    baseline_provenance: str
    severity: str
    adjustment_pct: float | None
    adjustment_provenance: str
    optimized_g_per_plant_day: float | None
    optimized_provenance: str
    plant_population: PlantPopulationOut
    total_g_per_day: float | None
    total_kg_per_day: float | None
    baseline_total_kg_per_day: float | None
    duration_days: float | None
    duration_provenance: str
    total_quantity_kg: float | None
    baseline_total_quantity_kg: float | None
    cost: CostResultOut
    expected_direction: str | None
    expected_direction_basis: str
    limitations: list[str]


class UnsupportedCategoryNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    action_label: str | None
    reason: str


class FarmConfigSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class OptimizationAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    crop: str
    assessment_day: int
    farm_configuration: FarmConfigSnapshotOut
    water_optimizations: list[WaterOptimizationOut]
    nutrient_optimizations: list[NutrientOptimizationOut]
    unsupported: list[UnsupportedCategoryNoteOut]
    multi_action_note: str | None
    limitations: list[str]


class FarmConfigurationIn(BaseModel):
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


class FarmConfigurationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    simulation_run_id: int
    crop: str
    field_area: float
    field_area_unit: str
    plant_population: int | None
    plant_spacing_m: float | None
    row_spacing_m: float | None
    cultivar: str | None
    irrigation_system_type: str | None
    irrigation_efficiency_pct: float | None
    available_water_l_per_day: float | None
    pump_capacity_l_per_hour: float | None
    pump_power_kw: float | None
    water_cost_per_liter: float | None
    fertilizer_cost_per_kg_n: float | None
    fertilizer_cost_per_kg_p2o5: float | None
    fertilizer_cost_per_kg_k2o: float | None
