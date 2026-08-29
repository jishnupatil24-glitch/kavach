import { useQuery } from '@tanstack/react-query';
import { getAnalysis } from '../endpoints/analysis';
import { getAssessment } from '../endpoints/assessment';
import { getDecision } from '../endpoints/decision';
import { getObservations } from '../endpoints/simulator';
import { qk } from '../queryKeys';
import { retry, STALE_5_MIN } from './queryConfig';

interface Opts {
  runId: number | null;
  day: number | null;
  enabled?: boolean;
}

export function useAnalysis({ runId, day, enabled = true }: Opts) {
  return useQuery({
    queryKey: qk.analysis(runId ?? -1, day),
    queryFn: () => getAnalysis(runId as number, day),
    enabled: enabled && runId != null,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useAssessment({ runId, day, enabled = true }: Opts) {
  return useQuery({
    queryKey: qk.assessment(runId ?? -1, day),
    queryFn: () => getAssessment(runId as number, day),
    enabled: enabled && runId != null,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useDecision({ runId, day, enabled = true }: Opts) {
  return useQuery({
    queryKey: qk.decision(runId ?? -1, day),
    queryFn: () => getDecision(runId as number, day),
    enabled: enabled && runId != null,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useObservations({ runId, day = null, enabled = true }: Opts) {
  return useQuery({
    queryKey: qk.observations(runId ?? -1, day),
    queryFn: () => getObservations(runId as number, day),
    enabled: enabled && runId != null,
    staleTime: STALE_5_MIN,
    retry,
  });
}
