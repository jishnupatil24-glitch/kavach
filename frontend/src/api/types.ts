/**
 * TypeScript mirror of docs/API_CONTRACT.md — verified against the FastAPI
 * route + Pydantic schema files in backend/app/.
 *
 * Rules:
 *  - Nullable JSON values are `T | null` (never optional-only).
 *  - Enum-shaped strings are string-literal unions.
 *  - No invented fields. If the backend returns extra keys they are ignored.
 *  - Phase 6 (Optimization* / FarmConfiguration*) types describe the CONTRACT.
 *    GET /api/optimization/tomato/runs/{id} is implemented and live.
 */

/* ============================ Enums ============================ */

export type Scenario =
  | 'normal'
  | 'heatwave'
  | 'water_shortage'
  | 'excess_irrigation'
  | 'high_humidity';

export type SeverityInput = 'mild' | 'moderate' | 'severe';

export type EvidenceStatus =
  | 'insufficient_data'
  | 'no_evidence'
  | 'weak_evidence'
  | 'corroborated_evidence';

export type Severity = 'insufficient_data' | 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';

export type Outcome =
  | 'ACTION_RECOMMENDED'
  | 'MONITOR'
  | 'NO_ACTION'
  | 'INSUFFICIENT_SUPPORT'
  | 'CONFLICT';

export type TrendDirection = 'RISING' | 'FALLING' | 'STABLE' | 'UNDETERMINED';

export type AbnormalTier = 'sourced_threshold' | 'icar_sign_trend_proxy';

export type Provenance = 'SOURCED' | 'PROJECT_DEFINED' | 'MODELED';

export type FeasibilityStatus = 'PASS' | 'FAIL' | 'NOT_EVALUATED';

export type CostStatus = 'AVAILABLE' | 'UNAVAILABLE';

export type PopulationSource = 'PROVIDED' | 'ESTIMATED' | 'UNKNOWN';

export type WaterDirection = 'increase' | 'decrease';

export type Nutrient = 'N' | 'P2O5' | 'K2O';

export type ParameterStatus =
  | 'sourced'
  | 'assumption'
  | 'missing'
  | 'source_needed'
  | 'derived'
  | 'context_dependent'
  | 'project_defined';

export type FieldAreaUnit = 'acre' | 'hectare' | 'm2';

export const PROBLEM_CATEGORIES = [
  'water_depletion',
  'excessive_moisture',
  'heat_related',
  'temperature_deficit',
  'humidity_low',
  'humidity_high',
  'nitrogen_related',
  'phosphorus_related',
  'potassium_related',
  'light_deficit',
] as const;
export type ProblemCategory = (typeof PROBLEM_CATEGORIES)[number];

/* ==================== Phase 0: reference ==================== */

export interface TomatoReferenceProfile {
  day: number;
  soil_moisture_pct: number;
  temperature_c: number;
  humidity_pct: number;
  dli_mol_m2_day: number;
  soil_n_mg_kg: number;
  soil_p_mg_kg: number;
  soil_k_mg_kg: number;
  n_demand_g_plant_day: number;
  p2o5_demand_g_plant_day: number;
  k2o_demand_g_plant_day: number;
}

/* ==================== Phase 1: agronomics ==================== */

export interface AgronomicSource {
  id: number;
  organization_or_author: string | null;
  title: string | null;
  publication_year: number | null;
  source_type: string | null;
  document_reference: string | null;
  description: string | null;
  notes: string | null;
}

export interface CropStage {
  id: number;
  crop: string;
  name: string;
  start_day: number | null;
  end_day: number | null;
  description: string | null;
  source_id: number | null;
  notes: string | null;
}

export interface AgronomicParameter {
  id: number;
  crop: string;
  domain: string;
  parameter_name: string;
  value_numeric: number | null;
  value_min: number | null;
  value_max: number | null;
  value_text: string | null;
  unit: string | null;
  stage_id: number | null;
  context: string | null;
  status: ParameterStatus;
  source_id: number | null;
  notes: string | null;
}

export interface StressCondition {
  id: number;
  crop: string;
  stress_type: string;
  affected_parameter: string;
  operator: string;
  threshold_value: number | null;
  unit: string | null;
  stage_id: number | null;
  severity: string | null;
  status: string;
  source_id: number | null;
  description: string | null;
  notes: string | null;
}

/* ==================== Phase 2: simulator ==================== */

export interface SimulationRunCreate {
  duration_days: number;
  scenario: Scenario;
  seed: number;
  severity: SeverityInput | null;
  scenario_start_day: number | null;
  scenario_duration_days: number | null;
}

export interface SimulationRun {
  id: number;
  crop: string;
  duration_days: number;
  scenario: Scenario;
  severity: SeverityInput | null;
  seed: number;
  scenario_start_day: number | null;
  scenario_duration_days: number | null;
  created_at: string;
}

export interface SensorObservation {
  id: number;
  simulation_run_id: number;
  day: number;
  hour: 0 | 6 | 12 | 18;
  temperature_c: number;
  humidity_pct: number;
  soil_moisture_pct: number;
  daily_dli_mol_m2_day: number;
  soil_n_mg_kg: number;
  soil_p_mg_kg: number;
  soil_k_mg_kg: number;
}

/* ==================== Phase 3: state analysis ==================== */

export interface CurrentState {
  parameter: string;
  field: string;
  value: number | null;
  day: number;
  n_readings: number;
  note: string | null;
}

export interface TrendState {
  parameter: string;
  direction: TrendDirection;
  rate_per_day: number | null;
  rate_unit: string | null;
  standard_error_per_day: number | null;
  stable_band: number | null;
  n_observations: number;
  note: string | null;
}

export interface PersistenceState {
  parameter: string;
  direction: TrendDirection;
  days: number;
  note: string | null;
}

export interface IcarState {
  parameter: string;
  current_value: number | null;
  icar_value: number | null;
  icar_day: number;
  signed_difference: number | null;
  absolute_difference: number | null;
  unit_suffix: string | null;
  note: string | null;
}

export interface AnalysisParameter {
  current: CurrentState;
  trend: TrendState;
  persistence: PersistenceState;
  icar: IcarState;
}

export interface AnalysisCropStage {
  stage_id: number;
  name: string;
  start_day: number | null;
  end_day: number | null;
  source_id: number | null;
}

export interface StateAnalysis {
  run_id: number;
  crop: string;
  analysis_day: number;
  duration_days: number;
  parameters: AnalysisParameter[];
  crop_stages: AnalysisCropStage[];
  agronomic_context: unknown[];
  data_quality_notes: string[];
}

/* ==================== Phase 4: problem assessment ==================== */

export interface RawRange {
  min_value: number | null;
  max_value: number | null;
  n_readings: number;
  label: string;
}

export interface SeverityFactors {
  deviation_ratio: number;
  deviation_score: number;
  intensity_ratio: number;
  intensity_score: number;
  duration_fraction: number;
  duration_score: number;
  total_score: number;
}

export interface AbnormalStateDuration {
  category: string;
  tier: AbnormalTier;
  days: number;
  provenance_note: string;
}

export interface Problem {
  category: ProblemCategory;
  label: string;
  field: string;
  status: EvidenceStatus;
  direction: TrendDirection | string | null;
  current_value: number | null;
  icar_value: number | null;
  icar_deviation: number | null;
  rate_per_day: number | null;
  rate_unit: string | null;
  persistence_days: number | null;
  sourced_corroboration_notes: string[];
  provenance_notes: string[];
  raw_range: RawRange;
  severity: Severity;
  severity_factors: SeverityFactors | null;
  severity_disclaimer: string;
  abnormal_state_duration: AbnormalStateDuration;
}

export interface StressAssessment {
  run_id: number;
  crop: string;
  assessment_day: number;
  problems: Problem[];
  crop_stages: AnalysisCropStage[];
}

/* ==================== Phase 5: decision engine ==================== */

export interface GateCheck {
  name: string;
  passed: boolean | null;
  detail: string;
}

export interface DecisionRecord {
  category: ProblemCategory;
  label: string;
  status: EvidenceStatus;
  severity: Severity;
  abnormal_duration_days: number | null;
  abnormal_duration_tier: AbnormalTier;
  eligibility_checks: GateCheck[];
  conflict_with: string | null;
  outcome: Outcome;
  action_label: string | null;
  action_type: string | null;
  action_basis: string;
  decision_provenance: string;
  quantitative_basis: null;
  limitations: string[];
  priority: number | null;
  priority_reason: string | null;
}

export interface DecisionAssessment {
  run_id: number;
  crop: string;
  assessment_day: number;
  decisions: DecisionRecord[];
}

/* ==================== Phase 6: optimization (CONTRACT) ==================== */

export interface FarmConfiguration {
  exists: boolean;
  crop: string | null;
  field_area: number | null;
  field_area_unit: FieldAreaUnit | null;
  plant_population: number | null;
  plant_spacing_m: number | null;
  row_spacing_m: number | null;
  cultivar: string | null;
  irrigation_system_type: string | null;
  irrigation_efficiency_pct: number | null;
  available_water_l_per_day: number | null;
  pump_capacity_l_per_hour: number | null;
  pump_power_kw: number | null;
  water_cost_per_liter: number | null;
  fertilizer_cost_per_kg_n: number | null;
  fertilizer_cost_per_kg_p2o5: number | null;
  fertilizer_cost_per_kg_k2o: number | null;
}

export interface FarmConfigurationOut extends Omit<FarmConfiguration, 'exists'> {
  simulation_run_id: number;
}

export type FarmConfigurationIn = Partial<{
  crop: string | null;
  field_area: number;
  field_area_unit: FieldAreaUnit;
  plant_population: number | null;
  plant_spacing_m: number | null;
  row_spacing_m: number | null;
  cultivar: string | null;
  irrigation_system_type: string | null;
  irrigation_efficiency_pct: number | null;
  available_water_l_per_day: number | null;
  pump_capacity_l_per_hour: number | null;
  pump_power_kw: number | null;
  water_cost_per_liter: number | null;
  fertilizer_cost_per_kg_n: number | null;
  fertilizer_cost_per_kg_p2o5: number | null;
  fertilizer_cost_per_kg_k2o: number | null;
}>;

export interface PlantPopulation {
  plants: number | null;
  source: PopulationSource;
  note: string;
}

export interface FeasibilityCheck {
  label: string;
  status: FeasibilityStatus;
  detail: string;
}

export interface CostBlock {
  status: CostStatus;
  baseline_cost: number | null;
  optimized_cost: number | null;
  cost_change: number | null;
  detail: string;
}

export interface WaterOptimization {
  category: ProblemCategory;
  action_label: string;
  direction: WaterDirection;
  stage_name: string | null;
  baseline_l_per_plant_day: number | null;
  baseline_provenance: Provenance;
  severity: Severity;
  adjustment_pct: number | null;
  adjustment_provenance: Provenance;
  optimized_l_per_plant_day: number | null;
  optimized_provenance: Provenance;
  /** How much MORE water a farmer typically applies than the theoretical
   *  requirement, absent decision support — a comparison point only, never
   *  measured/sourced farmer behavior. Always PROJECT_DEFINED. */
  typical_l_per_plant_day: number | null;
  typical_provenance: Provenance;
  typical_application_multiplier_pct: number | null;
  plant_population: PlantPopulation;
  baseline_l_per_day: number | null;
  optimized_l_per_day: number | null;
  typical_l_per_day: number | null;
  water_saved_l_per_day: number | null;
  water_saving_percentage: number | null;
  /** Positive = typical > KAVACH (real saving vs typical application).
   *  Negative = KAVACH > typical (render as "additional water required",
   *  never a saving). */
  water_saved_vs_typical_l_per_day: number | null;
  water_saved_vs_typical_percentage: number | null;
  review_cycle_days: number | null;
  review_cycle_provenance: Provenance;
  total_baseline_liters: number | null;
  total_optimized_liters: number | null;
  total_water_saved_liters: number | null;
  total_typical_liters: number | null;
  total_water_saved_vs_typical_liters: number | null;
  irrigation_efficiency_pct: number | null;
  irrigation_efficiency_source: string | null;
  delivered_baseline_l_per_day: number | null;
  delivered_optimized_l_per_day: number | null;
  feasibility: FeasibilityCheck[];
  cost: CostBlock;
  expected_direction: string;
  expected_direction_basis: string;
  limitations: string[];
}

export interface NutrientOptimization {
  category: ProblemCategory;
  nutrient: Nutrient;
  action_label: string;
  direction: 'increase';
  direction_basis: string;
  baseline_g_per_plant_day: number | null;
  baseline_provenance: 'SOURCED';
  severity: Severity;
  adjustment_pct: number | null;
  adjustment_provenance: Provenance;
  optimized_g_per_plant_day: number | null;
  optimized_provenance: Provenance;
  plant_population: PlantPopulation;
  total_g_per_day: number | null;
  total_kg_per_day: number | null;
  baseline_total_kg_per_day: number | null;
  duration_days: number | null;
  duration_provenance: Provenance;
  total_quantity_kg: number | null;
  baseline_total_quantity_kg: number | null;
  cost: CostBlock;
  expected_direction: string;
  expected_direction_basis: string;
  limitations: string[];
}

export interface UnsupportedAction {
  category: ProblemCategory;
  action_label: string;
  reason: string;
}

export interface OptimizationAssessment {
  run_id: number;
  crop: string;
  assessment_day: number;
  farm_configuration: FarmConfiguration;
  water_optimizations: WaterOptimization[];
  nutrient_optimizations: NutrientOptimization[];
  unsupported: UnsupportedAction[];
  multi_action_note: string | null;
  limitations: string[];
}
