import { api } from '../client';
import type { AgronomicParameter, AgronomicSource, CropStage, StressCondition } from '../types';

export function getParameters(params?: { status?: string; domain?: string }) {
  const sp = new URLSearchParams();
  if (params?.status) sp.set('status', params.status);
  if (params?.domain) sp.set('domain', params.domain);
  const q = sp.toString() ? `?${sp}` : '';
  return api.get<AgronomicParameter[]>(`/api/agronomics/tomato/parameters${q}`);
}

export function getCropStages() {
  return api.get<CropStage[]>('/api/agronomics/tomato/stages');
}

export function getSources() {
  return api.get<AgronomicSource[]>('/api/agronomics/tomato/sources');
}

export function getStressConditions() {
  return api.get<StressCondition[]>('/api/agronomics/tomato/stress-conditions');
}
