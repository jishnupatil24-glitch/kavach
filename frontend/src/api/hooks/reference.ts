import { useQuery } from '@tanstack/react-query';
import { getReferenceProfile } from '../endpoints/reference';
import { qk } from '../queryKeys';
import { retry } from './queryConfig';

/** ICAR reference profile is static for the run — cache it for the session. */
export function useReferenceProfile() {
  return useQuery({
    queryKey: qk.reference,
    queryFn: getReferenceProfile,
    staleTime: Infinity,
    gcTime: Infinity,
    retry,
  });
}
