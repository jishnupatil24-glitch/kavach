import { describe, expect, it } from 'vitest';
import { estimateRecoveryWindow } from './recoveryEstimate';

describe('estimateRecoveryWindow — frontend-only prototype, never a single-day claim', () => {
  it('produces a low/high range, never a single point estimate', () => {
    const w = estimateRecoveryWindow({
      severity: 'MODERATE',
      reviewCycleDays: 3,
      expectedDirection: 'FALLING',
    });
    expect(w).not.toBeNull();
    expect(w!.lowDays).toBeLessThanOrEqual(w!.highDays);
    expect(w!.confidence).toBe('LOW');
  });

  it('widens the range for higher severity', () => {
    const moderate = estimateRecoveryWindow({
      severity: 'MODERATE',
      reviewCycleDays: 3,
      expectedDirection: 'FALLING',
    })!;
    const critical = estimateRecoveryWindow({
      severity: 'CRITICAL',
      reviewCycleDays: 3,
      expectedDirection: 'FALLING',
    })!;
    expect(critical.highDays).toBeGreaterThan(moderate.highDays);
  });

  it('returns null (UNAVAILABLE) when review cycle is missing', () => {
    expect(
      estimateRecoveryWindow({ severity: 'HIGH', reviewCycleDays: null, expectedDirection: 'RISING' }),
    ).toBeNull();
  });

  it('returns null (UNAVAILABLE) when severity is insufficient_data', () => {
    expect(
      estimateRecoveryWindow({
        severity: 'insufficient_data',
        reviewCycleDays: 3,
        expectedDirection: 'RISING',
      }),
    ).toBeNull();
  });
});
