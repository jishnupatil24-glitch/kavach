import { api } from '../client';
import type { DecisionAssessment } from '../types';

export function getDecision(runId: number, day?: number | null) {
  const q = day != null ? `?day=${day}` : '';
  return api.get<DecisionAssessment>(`/api/decision/tomato/runs/${runId}${q}`);
}
