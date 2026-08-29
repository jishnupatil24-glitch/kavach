import { api } from '../client';
import type { StressAssessment } from '../types';

export function getAssessment(runId: number, day?: number | null) {
  const q = day != null ? `?day=${day}` : '';
  return api.get<StressAssessment>(`/api/assessment/tomato/runs/${runId}${q}`);
}
