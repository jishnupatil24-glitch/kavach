import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, Sprout } from 'lucide-react';
import { useRuns } from '@/api/hooks/runs';
import { PageHeader } from '@/components/primitives/PageHeader';
import { Button } from '@/components/primitives/Button';
import { EmptyState, ErrorState, SkeletonGrid } from '@/components/primitives/states';
import { Sheet } from '@/components/primitives/Sheet';
import { RunGenerateForm } from './RunGenerateForm';
import { RunCard } from './RunCard';

export function RunSwitcherPage() {
  const runs = useRuns();
  const navigate = useNavigate();
  const [genOpen, setGenOpen] = useState(false);

  const openGen = () => setGenOpen(true);

  return (
    <>
      <PageHeader
        eyebrow="KAVACH"
        title="Pick a simulation run"
        lead="Each run is a virtual polyhouse season. Open one to walk the decision funnel: farm state, problems, recommendations, and an optimized plan."
        actions={
          runs.data && runs.data.length > 0 ? (
            <Button variant="primary" onClick={openGen}>
              <Plus size={16} aria-hidden /> Generate a run
            </Button>
          ) : undefined
        }
      />

      {runs.isLoading ? (
        <SkeletonGrid count={6} />
      ) : runs.isError ? (
        <ErrorState error={runs.error} onRetry={() => runs.refetch()} />
      ) : !runs.data?.length ? (
        <EmptyState
          icon={<Sprout size={28} aria-hidden />}
          title="No runs yet"
          hint="Generate a demo run to begin. It creates a virtual season and runs every analysis phase before it returns."
          action={
            <Button variant="primary" onClick={openGen}>
              <Plus size={16} aria-hidden /> Generate a run
            </Button>
          }
        />
      ) : (
        <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {runs.data.map((r) => (
            <RunCard key={r.id} run={r} />
          ))}
        </div>
      )}

      <Sheet
        open={genOpen}
        onOpenChange={setGenOpen}
        title="Generate a simulation run"
        description="Severity and the stress window are required unless the scenario is “Normal conditions”."
      >
        <RunGenerateForm
          onCreated={(id) => {
            setGenOpen(false);
            navigate(`/runs/${id}`);
          }}
        />
      </Sheet>
    </>
  );
}
