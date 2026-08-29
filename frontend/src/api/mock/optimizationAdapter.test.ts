import { beforeEach, describe, expect, it } from 'vitest';
import {
  clearFarmConfigMock,
  getOptimizationMock,
  saveFarmConfigMock,
} from './optimizationAdapter';

const RUN = 99001;

describe('optimization mock adapter — contract-shaped, states preserved', () => {
  beforeEach(() => {
    // start each test from a clean in-memory config
    clearFarmConfigMock(RUN);
  });

  it('serves the happy fixture outside the development-stage window', async () => {
    saveFarmConfigMock(RUN, { field_area: 1, field_area_unit: 'acre', plant_population: 8000 });
    const res = await getOptimizationMock(RUN, 7);
    expect(res.run_id).toBe(RUN);
    expect(res.assessment_day).toBe(7);
    expect(res.water_optimizations[0].baseline_l_per_plant_day).not.toBeNull();
    expect(res.limitations).toContain('Prototype optimization model.');
  });

  it('serves the UNAVAILABLE fixture inside the development-stage window (day 27-62)', async () => {
    saveFarmConfigMock(RUN, { field_area: 1, field_area_unit: 'acre', plant_population: 8000 });
    const res = await getOptimizationMock(RUN, 37);
    const w = res.water_optimizations[0];
    expect(w.baseline_l_per_plant_day).toBeNull();
    expect(w.cost.status).toBe('UNAVAILABLE');
    expect(w.feasibility.every((f) => f.status === 'NOT_EVALUATED')).toBe(true);
  });

  it('produces UNKNOWN population + null field totals when no config is set', async () => {
    const res = await getOptimizationMock(RUN, 7);
    const w = res.water_optimizations[0];
    expect(res.farm_configuration.exists).toBe(false);
    expect(w.plant_population.source).toBe('UNKNOWN');
    expect(w.plant_population.plants).toBeNull();
    expect(w.baseline_l_per_day).toBeNull();
    expect(w.cost.status).toBe('UNAVAILABLE');
  });

  it('saveFarmConfig upserts and flips exists once area + unit are present', async () => {
    const partial = await saveFarmConfigMock(RUN, { plant_population: 5000 });
    expect(partial.simulation_run_id).toBe(RUN);
    const full = await saveFarmConfigMock(RUN, { field_area: 2, field_area_unit: 'hectare' });
    expect(full.field_area).toBe(2);
    const res = await getOptimizationMock(RUN, 7);
    expect(res.farm_configuration.exists).toBe(true);
  });
});
