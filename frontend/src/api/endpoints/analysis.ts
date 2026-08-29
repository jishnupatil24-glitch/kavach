import { api } from '../client';
import type { StateAnalysis } from '../types';

export function getAnalysis(runId: number, day?: number | null) {
  const q = day != null ? `?day=${day}` : '';
  return api.get<StateAnalysis>(`/api/analysis/tomato/runs/${runId}${q}`);
}
