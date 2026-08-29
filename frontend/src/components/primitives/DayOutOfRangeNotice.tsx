import { useRunContext } from '@/context/RunContext';
import { Button } from './Button';

/** Shown when the ?day= URL param is outside 1..N for the current run. */
export function DayOutOfRangeNotice({ max }: { max: number | null }) {
  const { setDay, durationDays } = useRunContext();
  const limit = max ?? durationDays ?? 1;
  return (
    <div
      role="alert"
      className="rounded-lg border border-sev-high/40 bg-sev-high/5 px-5 py-4"
    >
      <p className="font-sans font-medium text-ink">Day out of range for this run (1–{limit}).</p>
      <p className="mt-1 text-sm text-body">
        Pick a day inside the run to see its analysis.
      </p>
      <Button size="sm" variant="secondary" className="mt-3" onClick={() => setDay(limit)}>
        Go to day {limit}
      </Button>
    </div>
  );
}
