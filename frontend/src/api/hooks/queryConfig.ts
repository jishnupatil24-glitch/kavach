import { ApiError } from '../client';

/** Shared query defaults: 5-min freshness, one retry on network, none on 4xx. */
export const STALE_5_MIN = 5 * 60 * 1000;

export function retry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.httpStatus >= 400 && error.httpStatus < 500) return false;
  return failureCount < 1;
}
