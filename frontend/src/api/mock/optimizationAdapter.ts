/**
 * Phase 6 mock adapter.
 *
 * Phase 6 (Quantitative Optimization) is documented in docs/API_CONTRACT.md but
 * the route is NOT mounted in backend/app/main.py yet. Until it ships, the
 * optimization + farm-config views run on this adapter, which serves the two
 * contract-shaped fixtures captured from the docs:
 *
 *   - optimization.happy.json         run 582 / day 7  (full numeric chain)
 *   - optimization.unavailable.json   run 584 / day 37 (honest UNAVAILABLE case)
 *
 * The adapter keeps an in-memory farm-config store so Farm Setup has a visible
 * effect and the UNKNOWN-population / missing-config states can be demoed.
 * Nothing here is a real computation — every value stays flagged as prototype.
 */
import type {
  FarmConfiguration,
  FarmConfigurationIn,
  FarmConfigurationOut,
  FeasibilityCheck,
  OptimizationAssessment,
  WaterOptimization,
} from '../types';
import happyFixture from './fixtures/optimization.happy.json';
import unavailableFixture from './fixtures/optimization.unavailable.json';

const FIXTURE_POPULATION = 8000;
const DEV_STAGE_START = 27;
const DEV_STAGE_END = 62;

const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v)) as T;

const store = new Map<number, FarmConfiguration>();

function seededConfig(): FarmConfiguration {
  return clone(happyFixture.farm_configuration) as unknown as FarmConfiguration;
}

function getConfig(runId: number): FarmConfiguration {
  if (!store.has(runId)) store.set(runId, seededConfig());
  return store.get(runId)!;
}

function nullFieldTotals(opt: WaterOptimization): void {
  opt.baseline_l_per_day = null;
  opt.optimized_l_per_day = null;
  opt.water_saved_l_per_day = null;
  opt.water_saving_percentage = null;
  opt.total_baseline_liters = null;
  opt.total_optimized_liters = null;
  opt.total_water_saved_liters = null;
  opt.delivered_baseline_l_per_day = null;
  opt.delivered_optimized_l_per_day = null;
  opt.feasibility = opt.feasibility.map(
    (f): FeasibilityCheck => ({
      ...f,
      status: 'NOT_EVALUATED',
      detail: 'Whole-field quantity is unknown in the prototype — feasibility not evaluated.',
    }),
  );
  opt.cost = {
    status: 'UNAVAILABLE',
    baseline_cost: null,
    optimized_cost: null,
    cost_change: null,
    detail: 'Whole-field quantity is unknown in the prototype — cost unavailable.',
  };
}

export async function getOptimizationMock(
  runId: number,
  day: number,
): Promise<OptimizationAssessment> {
  const inDevStage = day >= DEV_STAGE_START && day <= DEV_STAGE_END;
  const base = clone(
    inDevStage ? unavailableFixture : happyFixture,
  ) as unknown as OptimizationAssessment;

  base.run_id = runId;
  base.assessment_day = day;

  const cfg = getConfig(runId);
  base.farm_configuration = clone(cfg);

  const populationKnown = cfg.exists && cfg.plant_population != null;
  const populationChanged = populationKnown && cfg.plant_population !== FIXTURE_POPULATION;

  for (const opt of base.water_optimizations) {
    if (!populationKnown) {
      // Per-plant baseline/optimized stay as the fixture gives them; only the
      // whole-field figures that depend on population are withheld.
      opt.plant_population = {
        plants: null,
        source: 'UNKNOWN',
        note: 'No plant population configured — set it in Farm Setup to see whole-field totals.',
      };
      nullFieldTotals(opt);
    } else {
      opt.plant_population = {
        plants: cfg.plant_population!,
        source: 'PROVIDED',
        note: 'Explicit plant_population from farm configuration.',
      };
      if (populationChanged) {
        nullFieldTotals(opt);
        opt.limitations = [
          ...opt.limitations,
          'Whole-field totals are not recomputed in the prototype after a plant-population change.',
        ];
      } else if (cfg.water_cost_per_liter == null) {
        opt.cost = {
          status: 'UNAVAILABLE',
          baseline_cost: null,
          optimized_cost: null,
          cost_change: null,
          detail: 'No water cost rate configured — cost unavailable.',
        };
      }
    }
  }

  return base;
}

export async function saveFarmConfigMock(
  runId: number,
  body: FarmConfigurationIn,
): Promise<FarmConfigurationOut> {
  const current = store.has(runId)
    ? store.get(runId)!
    : ({
        exists: false,
        crop: 'tomato',
        field_area: null,
        field_area_unit: null,
        plant_population: null,
        plant_spacing_m: null,
        row_spacing_m: null,
        cultivar: null,
        irrigation_system_type: null,
        irrigation_efficiency_pct: null,
        available_water_l_per_day: null,
        pump_capacity_l_per_hour: null,
        pump_power_kw: null,
        water_cost_per_liter: null,
        fertilizer_cost_per_kg_n: null,
        fertilizer_cost_per_kg_p2o5: null,
        fertilizer_cost_per_kg_k2o: null,
      } satisfies FarmConfiguration);

  const merged: FarmConfiguration = { ...current };
  for (const [k, v] of Object.entries(body)) {
    if (v !== undefined) (merged as Record<string, unknown>)[k] = v;
  }
  merged.exists = merged.field_area != null && merged.field_area_unit != null;
  store.set(runId, merged);

  const out: FarmConfigurationOut = {
    simulation_run_id: runId,
    crop: merged.crop,
    field_area: merged.field_area,
    field_area_unit: merged.field_area_unit,
    plant_population: merged.plant_population,
    plant_spacing_m: merged.plant_spacing_m,
    row_spacing_m: merged.row_spacing_m,
    cultivar: merged.cultivar,
    irrigation_system_type: merged.irrigation_system_type,
    irrigation_efficiency_pct: merged.irrigation_efficiency_pct,
    available_water_l_per_day: merged.available_water_l_per_day,
    pump_capacity_l_per_hour: merged.pump_capacity_l_per_hour,
    pump_power_kw: merged.pump_power_kw,
    water_cost_per_liter: merged.water_cost_per_liter,
    fertilizer_cost_per_kg_n: merged.fertilizer_cost_per_kg_n,
    fertilizer_cost_per_kg_p2o5: merged.fertilizer_cost_per_kg_p2o5,
    fertilizer_cost_per_kg_k2o: merged.fertilizer_cost_per_kg_k2o,
  };
  return out;
}

/** Prototype affordance: wipe the in-memory config to demo the "not set" state. */
export function clearFarmConfigMock(runId: number): void {
  store.set(runId, {
    exists: false,
    crop: 'tomato',
    field_area: null,
    field_area_unit: null,
    plant_population: null,
    plant_spacing_m: null,
    row_spacing_m: null,
    cultivar: null,
    irrigation_system_type: null,
    irrigation_efficiency_pct: null,
    available_water_l_per_day: null,
    pump_capacity_l_per_hour: null,
    pump_power_kw: null,
    water_cost_per_liter: null,
    fertilizer_cost_per_kg_n: null,
    fertilizer_cost_per_kg_p2o5: null,
    fertilizer_cost_per_kg_k2o: null,
  });
}
