import { Link } from 'react-router-dom';
import { ArrowRight, CalendarDays } from 'lucide-react';
import type { SimulationRun } from '@/api/types';
import { formatDate } from '@/lib/format';
import { SCENARIO, SEVERITY_INPUT } from '@/lib/plain-language';
import { runSubLabel } from './runLabel';

export function RunCard({ run }: { run: SimulationRun }) {
  const scen = SCENARIO[run.scenario];
  return (
    <Link
      to={`/runs/${run.id}`}
      className="group flex flex-col rounded-lg border border-hairline bg-surface p-5 shadow-card transition-all hover:-translate-y-0.5 hover:shadow-lift"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-sans text-xs font-semibold uppercase tracking-wide text-brand-700">
            Run #{run.id}
          </p>
          <h3 className="mt-1 font-display text-xl font-semibold text-ink">{scen?.plain ?? run.scenario}</h3>
        </div>
        {run.severity ? (
          <span className="rounded-pill border border-hairline px-2 py-0.5 text-xs text-muted">
            {SEVERITY_INPUT[run.severity] ?? run.severity}
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-sm text-body">{scen?.description}</p>
      <p className="mt-3 flex items-center gap-1.5 text-xs text-muted">
        <CalendarDays size={13} aria-hidden />
        {runSubLabel(run)}
      </p>
      <p className="mt-1 text-xs text-muted">Created {formatDate(run.created_at)}</p>
      <span className="mt-4 inline-flex items-center gap-1 font-sans text-sm font-medium text-brand-700">
        Open run
        <ArrowRight size={15} aria-hidden className="transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
