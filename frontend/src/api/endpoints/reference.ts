import { api } from '../client';
import type { TomatoReferenceProfile } from '../types';

export function getReferenceProfile() {
  return api.get<TomatoReferenceProfile[]>('/api/reference/tomato');
}

export function getReferenceDay(day: number) {
  return api.get<TomatoReferenceProfile>(`/api/reference/tomato/day/${day}`);
}
