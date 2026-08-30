import { describe, expect, it } from 'vitest';
import { classifyWaterImpact } from './waterImpact';

/**
 * Mirrors the backend's own sign convention exactly (see
 * app/services/optimization/water_model.py): the caller always passes
 * `typical - kavach` and its derived percentage — this function only
 * decides how to LABEL that already-computed number, never recomputes it.
 */
describe('classifyWaterImpact', () => {
  it('case 1: typical 30,000 vs KAVACH 25,920 -> 4,080 L/day saved (13.6%)', () => {
    const r = classifyWaterImpact(4080, (4080 / 30000) * 100);
    expect(r.kind).toBe('saved');
    expect(r.magnitudePerDay).toBeCloseTo(4080, 5);
    expect(r.magnitudePct).toBeCloseTo(13.6, 1);
  });

  it('case 2: typical 30,000 vs KAVACH 15,120 -> 14,880 L/day saved (49.6%)', () => {
    const r = classifyWaterImpact(14880, (14880 / 30000) * 100);
    expect(r.kind).toBe('saved');
    expect(r.magnitudePerDay).toBeCloseTo(14880, 5);
    expect(r.magnitudePct).toBeCloseTo(49.6, 1);
  });

  it('case 3: typical 25,000 vs KAVACH 30,000 -> additional water required, never "saved"', () => {
    const delta = 25000 - 30000; // -5000
    const r = classifyWaterImpact(delta, (delta / 25000) * 100);
    expect(r.kind).toBe('additional');
    expect(r.magnitudePerDay).toBeCloseTo(5000, 5);
    expect(r.magnitudePct).toBeCloseTo(20, 5);
  });

  it('case 4: typical UNKNOWN -> UNAVAILABLE, never coerced to a 0/positive saving', () => {
    const r = classifyWaterImpact(null, null);
    expect(r.kind).toBe('unavailable');
    expect(r.magnitudePerDay).toBeNull();
    expect(r.magnitudePct).toBeNull();
  });

  it('case 5: typical === KAVACH -> 0 L/day, no misleading positive saving', () => {
    const r = classifyWaterImpact(0, 0);
    expect(r.kind).toBe('equal');
    expect(r.magnitudePerDay).toBe(0);
  });
});
