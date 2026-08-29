import { api } from '../client';
import type { SensorObservation, SimulationRun, SimulationRunCreate } from '../types';

export function listRuns() {
  return api.get<SimulationRun[]>('/api/simulator/runs');
}

export function getRun(runId: number) {
  return api.get<SimulationRun>(`/api/simulator/runs/${runId}`);
}

export function createRun(body: SimulationRunCreate) {
  return api.post<SimulationRun>('/api/simulator/runs', body);
}

export function getObservations(runId: number, day?: number | null) {
  const q = day != null ? `?day=${day}` : '';
  return api.get<SensorObservation[]>(`/api/simulator/runs/${runId}/observations${q}`);
}
