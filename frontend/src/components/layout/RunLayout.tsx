import { Outlet } from 'react-router-dom';
import { RunProvider, useRunContext } from '@/context/RunContext';
import { AppShell } from './AppShell';
import { RunNotFound } from '@/pages/RunNotFound';
import { ErrorState, SkeletonCard } from '@/components/primitives/states';

function RunLayoutInner() {
  const { runId, isLoadingRun, runNotFound, runError } = useRunContext();

  return (
    <AppShell>
      {runNotFound ? (
        <RunNotFound runId={runId} />
      ) : runError ? (
        <ErrorState error={runError} />
      ) : isLoadingRun ? (
        <SkeletonCard lines={4} />
      ) : (
        <Outlet />
      )}
    </AppShell>
  );
}

/** Wraps every /runs/:id/* route with the run + day URL-state provider. */
export function RunLayout() {
  return (
    <RunProvider>
      <RunLayoutInner />
    </RunProvider>
  );
}
