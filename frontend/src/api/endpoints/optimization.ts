/**
 * Phase 6 endpoint facade.
 *
 * Phase 6 (optimization + farm-config) IS implemented and mounted in
 * `backend/app/main.py`, so the real API is the default.
 *
 * VITE_MOCK_OPTIMIZATION unset / =false -> the real endpoints below (default).
 * VITE_MOCK_OPTIMIZATION=true           -> the in-memory mock adapter, an
 *                                          opt-in dev fallback for demoing the
 *                                          UI with the backend offline.
 *
 * UI code imports only from here, so flipping the flag needs zero component
 * changes.
 */
import { api } from '../client';
import type {
  FarmConfigurationIn,
  FarmConfigurationOut,
  OptimizationAssessment,
} from '../types';
import {
  clearFarmConfigMock,
  getOptimizationMock,
  saveFarmConfigMock,
} from '../mock/optimizationAdapter';

export const OPTIMIZATION_IS_MOCKED =
  (import.meta.env.VITE_MOCK_OPTIMIZATION ?? 'false').toLowerCase() === 'true';

export function getOptimization(runId: number, day: number): Promise<OptimizationAssessment> {
  if (OPTIMIZATION_IS_MOCKED) return getOptimizationMock(runId, day);
  return api.get<OptimizationAssessment>(`/api/optimization/tomato/runs/${runId}?day=${day}`);
}

export function saveFarmConfig(
  runId: number,
  body: FarmConfigurationIn,
): Promise<FarmConfigurationOut> {
  if (OPTIMIZATION_IS_MOCKED) return saveFarmConfigMock(runId, body);
  return api.post<FarmConfigurationOut>(`/api/optimization/tomato/runs/${runId}/farm-config`, body);
}

/** Prototype-only: no real backend equivalent. */
export function clearFarmConfig(runId: number): void {
  if (OPTIMIZATION_IS_MOCKED) clearFarmConfigMock(runId);
}
