import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { useRunContext } from '@/context/RunContext';
import { cn } from '@/lib/cn';

export function DayScrubber({ className }: { className?: string }) {
  const { day, rawDay, durationDays, stepDay, setDay, dayOutOfRange } = useRunContext();
  const [draft, setDraft] = useState(String(day));

  useEffect(() => setDraft(String(day)), [day]);

  const max = durationDays ?? day;
  const commit = () => {
    const n = Number(draft);
    if (Number.isFinite(n)) setDay(Math.min(Math.max(1, Math.round(n)), max));
    else setDraft(String(day));
  };

  // No explicit ?day= in the URL -> viewing the run's latest day, i.e. the
  // CURRENT optimized action plan. An explicit day (any day, including the
  // last one once typed in) is a HISTORICAL lookup at that point in time —
  // matches the backend's own current/historical semantics (no computed
  // "latest" concept exists server-side; "current" is simply this run's
  // last day, re-run on demand).
  const isCurrent = rawDay == null;

  return (
    <div className={cn('inline-flex items-center gap-2', className)}>
      <span
        className={cn(
          'hidden shrink-0 rounded-full px-2 py-0.5 font-sans text-xs font-medium sm:inline-block',
          isCurrent
            ? 'bg-brand-tint text-brand-900'
            : 'border border-hairline text-muted',
        )}
        title={
          isCurrent
            ? 'Current optimized action plan — this run’s latest day'
            : 'Historical — viewing a specific past day, not a new calculation'
        }
      >
        {isCurrent ? 'Current plan' : 'Historical'}
      </span>
      <div
        className={cn(
          'inline-flex items-center gap-1 rounded-pill border border-hairline bg-surface px-1',
          dayOutOfRange && 'border-sev-high',
        )}
      >
      <button
        type="button"
        aria-label="Previous day"
        onClick={() => stepDay(-1)}
        disabled={day <= 1}
        className="flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-40"
      >
        <ChevronLeft size={16} aria-hidden />
      </button>
      <label className="flex items-center gap-1 px-1 font-sans text-sm text-body">
        <span className="text-muted">Day</span>
        <input
          value={draft}
          inputMode="numeric"
          onChange={(e) => setDraft(e.target.value.replace(/[^\d]/g, ''))}
          onBlur={commit}
          onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
          aria-label={`Day, 1 to ${max}`}
          className="w-10 bg-transparent text-center font-mono text-sm text-ink focus:outline-none"
        />
        <span className="text-muted">/ {durationDays ?? '—'}</span>
      </label>
      <button
        type="button"
        aria-label="Next day"
        onClick={() => stepDay(1)}
        disabled={day >= max}
        className="flex h-9 w-9 items-center justify-center rounded-full text-muted hover:bg-surface-sunken hover:text-ink disabled:opacity-40"
      >
        <ChevronRight size={16} aria-hidden />
      </button>
      </div>
    </div>
  );
}
