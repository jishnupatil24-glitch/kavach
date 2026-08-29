import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createRun, getRun, listRuns } from '../endpoints/simulator';
import { qk } from '../queryKeys';
import type { SimulationRunCreate } from '../types';
import { retry, STALE_5_MIN } from './queryConfig';

export function useRuns() {
  return useQuery({ queryKey: qk.runs, queryFn: listRuns, staleTime: STALE_5_MIN, retry });
}

export function useRun(runId: number | null) {
  return useQuery({
    queryKey: qk.run(runId ?? -1),
    queryFn: () => getRun(runId as number),
    enabled: runId != null,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useCreateRun() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: SimulationRunCreate) => createRun(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.runs }),
  });
}
