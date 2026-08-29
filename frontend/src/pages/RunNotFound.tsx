import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useRuns } from '@/api/hooks/runs';
import { runLabel, runSubLabel } from '@/features/runs/runLabel';
import { Button } from '@/components/primitives/Button';
import { Sheet } from '@/components/primitives/Sheet';
import { RunGenerateForm } from '@/features/runs/RunGenerateForm';

export function RunNotFound({ runId }: { runId: number | string }) {
  const runs = useRuns();
  const navigate = useNavigate();
  const [genOpen, setGenOpen] = useState(false);

  return (
    <div className="mx-auto max-w-lg py-16 text-center">
      <p className="font-display text-3xl font-semibold text-ink">Run not found</p>
      <p className="mt-2 text-body">
        There is no simulation run <span className="font-mono">#{String(runId)}</span>. Pick one
        below or generate a new one.
      </p>

      <div className="mt-8 space-y-2 text-left">
        {runs.data?.slice(0, 6).map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => navigate(`/runs/${r.id}`)}
            className="flex w-full items-center justify-between rounded-lg border border-hairline bg-surface px-4 py-3 text-left hover:bg-surface-sunken"
          >
            <span>
              <span className="block font-sans text-sm font-medium text-ink">{runLabel(r)}</span>
              <span className="block text-xs text-muted">{runSubLabel(r)}</span>
            </span>
          </button>
        ))}
      </div>

      <Button variant="primary" className="mt-6" onClick={() => setGenOpen(true)}>
        Generate a run
      </Button>

      <Sheet open={genOpen} onOpenChange={setGenOpen} title="Generate a simulation run">
        <RunGenerateForm
          onCreated={(id) => {
            setGenOpen(false);
            navigate(`/runs/${id}`);
          }}
        />
      </Sheet>
    </div>
  );
}
