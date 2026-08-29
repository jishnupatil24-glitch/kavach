import { useQuery } from '@tanstack/react-query';
import {
  getCropStages,
  getParameters,
  getSources,
  getStressConditions,
} from '../endpoints/agronomics';
import { qk } from '../queryKeys';
import { retry, STALE_5_MIN } from './queryConfig';

export function useAgronomicParameters(filter?: { status?: string; domain?: string }) {
  return useQuery({
    queryKey: qk.agronomicParameters(filter?.status, filter?.domain),
    queryFn: () => getParameters(filter),
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useCropStages() {
  return useQuery({
    queryKey: qk.cropStages,
    queryFn: getCropStages,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useAgronomicSources() {
  return useQuery({
    queryKey: qk.agronomicSources,
    queryFn: getSources,
    staleTime: STALE_5_MIN,
    retry,
  });
}

export function useStressConditions() {
  return useQuery({
    queryKey: ['agronomics', 'stress-conditions'],
    queryFn: getStressConditions,
    staleTime: STALE_5_MIN,
    retry,
  });
}
