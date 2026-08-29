import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as Popover from '@radix-ui/react-popover';
import { Check, ChevronsUpDown, Plus } from 'lucide-react';
import { useRuns } from '@/api/hooks/runs';
import { useMaybeRunContext } from '@/context/RunContext';
import { runLabel, runSubLabel } from '@/features/runs/runLabel';
import { RunGenerateForm } from '@/features/runs/RunGenerateForm';
import { Sheet } from '@/components/primitives/Sheet';
import { cn } from '@/lib/cn';

export function RunSwitcher() {
  const runs = useRuns();
  const run = useMaybeRunContext();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [genOpen, setGenOpen] = useState(false);

  const current = run?.run;
  const label = current ? `Run #${current.id} · ${runLabel(current)}` : 'Select a run';

  return (
    <>
      <Popover.Root open={open} onOpenChange={setOpen}>
        <Popover.Trigger asChild>
          <button
            type="button"
            className="inline-flex max-w-[62vw] items-center gap-2 rounded-pill border border-hairline bg-surface px-3 py-1.5 font-sans text-sm text-ink hover:bg-surface-sunken sm:max-w-none"
          >
            <span className="truncate">{label}</span>
            <ChevronsUpDown size={14} aria-hidden className="shrink-0 text-muted" />
          </button>
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={6}
            className="z-50 w-[320px] rounded-lg border border-hairline bg-surface p-2 shadow-lift"
          >
            <div className="flex items-center justify-between px-2 py-1">
              <span className="font-sans text-xs font-semibold uppercase tracking-wide text-muted">
                Simulation runs
              </span>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setGenOpen(true);
                }}
                className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs text-brand-700 hover:bg-brand-tint"
              >
                <Plus size={13} aria-hidden /> New run
              </button>
            </div>
            <div className="max-h-72 overflow-y-auto">
              {runs.isLoading ? (
                <p className="px-2 py-3 text-sm text-muted">Loading runs…</p>
              ) : runs.isError ? (
                <p className="px-2 py-3 text-sm text-sev-high">Could not load runs.</p>
              ) : !runs.data?.length ? (
                <p className="px-2 py-3 text-sm text-muted">
                  No runs yet. Create one with “New run”.
                </p>
              ) : (
                <ul>
                  {runs.data.map((r) => {
                    const active = r.id === current?.id;
                    return (
                      <li key={r.id}>
                        <button
                          type="button"
                          onClick={() => {
                            setOpen(false);
                            navigate(`/runs/${r.id}`);
                          }}
                          className={cn(
                            'flex w-full items-start gap-2 rounded px-2 py-2 text-left hover:bg-surface-sunken',
                            active && 'bg-brand-tint',
                          )}
                        >
                          <Check
                            size={15}
                            aria-hidden
                            className={cn('mt-0.5 shrink-0', active ? 'text-brand-700' : 'opacity-0')}
                          />
                          <span className="min-w-0">
                            <span className="block truncate font-sans text-sm text-ink">
                              {runLabel(r)}
                            </span>
                            <span className="block truncate text-xs text-muted">
                              {runSubLabel(r)}
                            </span>
                          </span>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>

      <Sheet
        open={genOpen}
        onOpenChange={setGenOpen}
        title="Generate a simulation run"
        description="Pick a scenario. Severity and the stress window are required unless the scenario is “Normal conditions”."
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
