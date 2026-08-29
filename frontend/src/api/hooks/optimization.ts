import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { getOptimization, saveFarmConfig } from '../endpoints/optimization';
import { qk } from '../queryKeys';
import type { FarmConfigurationIn } from '../types';
import { retry, STALE_5_MIN } from './queryConfig';

export function useOptimization(runId: number | null, day: number | null) {
  return useQuery({
    queryKey: qk.optimization(runId ?? -1, day),
    queryFn: () => getOptimization(runId as number, day as number),
    enabled: runId != null && day != null,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useSaveFarmConfig(runId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: FarmConfigurationIn) => saveFarmConfig(runId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['optimization', runId] }),
  });
}
