import { formatNumber, formatPercent, isMissing } from '@/lib/format';
import { UnavailableValue } from '@/components/status/UnavailableValue';

/**
 * Modelled water change. Rendered in neutral "modeled blue" — never the healthy
 * green — so a prototype figure is never read as a validated win.
 * Sign convention (from the contract): negative saved / negative percentage =
 * MORE water needed (the water_depletion "increase" case).
 */
export function SavingsPanel({
  savedPerDay,
  savingPct,
  totalSaved,
  reviewCycleDays,
  why,
  label,
}: {
  savedPerDay: number | null;
  savingPct: number | null;
  totalSaved: number | null;
  reviewCycleDays: number | null;
  why?: string;
  /** Override the default "Modelled water saved / extra water needed" heading. */
  label?: string;
}) {
  if (isMissing(savedPerDay) && isMissing(savingPct)) {
    return (
      <UnavailableValue
        kind="unavailable"
        why={why ?? 'Whole-field water quantity is unavailable, so the change cannot be computed.'}
      />
    );
  }

  const more = (savedPerDay ?? savingPct ?? 0) < 0;
  const magPerDay = savedPerDay != null ? Math.abs(savedPerDay) : null;
  const magPct = savingPct != null ? Math.abs(savingPct) : null;
  const magTotal = totalSaved != null ? Math.abs(totalSaved) : null;

  return (
    <div className="rounded-lg border border-modeled/30 bg-modeled/5 p-4">
      <p className="font-sans text-sm font-medium text-modeled">
        {label ?? (more ? 'Modelled extra water needed' : 'Modelled water saved')}
      </p>
      <p className="mt-1 font-display text-2xl font-semibold text-modeled">
        {magPerDay != null ? `${formatNumber(magPerDay, 0)} L/day` : '—'}
        {magPct != null ? (
          <span className="ml-2 font-sans text-base">({formatPercent(magPct)})</span>
        ) : null}
      </p>
      {magTotal != null ? (
        <p className="mt-1 text-sm text-body">
          {formatNumber(magTotal, 0)} L over the {reviewCycleDays ?? '—'}-day review cycle
        </p>
      ) : null}
      <p className="mt-2 text-xs text-muted">
        Review cycle is an operational re-check cadence, not a claim about crop recovery time.
      </p>
    </div>
  );
}
