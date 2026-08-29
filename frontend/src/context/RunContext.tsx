import { createContext, useCallback, useContext, useMemo } from 'react';
import type { ReactNode } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useRun } from '@/api/hooks/runs';
import type { SimulationRun } from '@/api/types';
import { ApiError } from '@/api/client';

interface RunCtx {
  runId: number;
  run: SimulationRun | undefined;
  durationDays: number | null;
  /** `day` from the URL, or null when absent. */
  rawDay: number | null;
  /** rawDay, or the run's last day when absent (the API's own default). */
  day: number;
  /** rawDay is present AND outside 1..durationDays. */
  dayOutOfRange: boolean;
  setDay: (day: number) => void;
  stepDay: (delta: number) => void;
  isLoadingRun: boolean;
  runNotFound: boolean;
  runError: ApiError | null;
}

const Ctx = createContext<RunCtx | null>(null);

export function RunProvider({ children }: { children: ReactNode }) {
  const { id } = useParams();
  const runId = Number(id);
  const [params, setParams] = useSearchParams();

  const runQuery = useRun(Number.isFinite(runId) ? runId : null);
  const run = runQuery.data;
  const durationDays = run?.duration_days ?? null;

  const dayParam = params.get('day');
  const rawDay = dayParam != null && dayParam !== '' ? Number(dayParam) : null;
  const rawDayValid = rawDay != null && Number.isFinite(rawDay);

  const day = rawDayValid ? (rawDay as number) : (durationDays ?? 1);

  const dayOutOfRange =
    rawDayValid && durationDays != null && ((rawDay as number) < 1 || (rawDay as number) > durationDays);

  const setDay = useCallback(
    (d: number) => {
      const next = new URLSearchParams(params);
      next.set('day', String(d));
      setParams(next, { replace: false });
    },
    [params, setParams],
  );

  const stepDay = useCallback(
    (delta: number) => {
      const max = durationDays ?? day;
      const next = Math.min(Math.max(1, day + delta), max);
      setDay(next);
    },
    [day, durationDays, setDay],
  );

  const runError = runQuery.error instanceof ApiError ? runQuery.error : null;
  const runIdValid = Number.isFinite(runId) && runId > 0;
  const runNotFound = !runIdValid || runError?.httpStatus === 404;

  const value = useMemo<RunCtx>(
    () => ({
      runId,
      run,
      durationDays,
      rawDay: rawDayValid ? (rawDay as number) : null,
      day,
      dayOutOfRange: Boolean(dayOutOfRange),
      setDay,
      stepDay,
      isLoadingRun: runQuery.isLoading,
      runNotFound,
      runError,
    }),
    [
      runId,
      run,
      durationDays,
      rawDayValid,
      rawDay,
      day,
      dayOutOfRange,
      setDay,
      stepDay,
      runQuery.isLoading,
      runNotFound,
      runError,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useRunContext(): RunCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error('useRunContext must be used within RunProvider');
  return v;
}

/** Returns the run context if present, or null on global (non-run) routes. */
export function useMaybeRunContext(): RunCtx | null {
  return useContext(Ctx);
}
