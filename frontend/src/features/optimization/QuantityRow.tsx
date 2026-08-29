import type { ReactNode } from 'react';
import { formatNumber } from '@/lib/format';
import { ProvenanceDot } from '@/components/status/Provenance';
import { UnavailableValue } from '@/components/status/UnavailableValue';

/**
 * A labelled quantity with its provenance dot, or one of the three explicit
 * "no number" states. Never prints 0 for a withheld value.
 */
export function QuantityRow({
  label,
  value,
  unit,
  provenance,
  precision = 2,
  missingKind = 'unavailable',
  why,
  action,
  emphasis,
}: {
  label: ReactNode;
  value: number | null | undefined;
  unit?: string;
  provenance?: string | null;
  precision?: number;
  missingKind?: 'unavailable' | 'unknown' | 'not-evaluated';
  why?: ReactNode;
  action?: ReactNode;
  emphasis?: boolean;
}) {
  const n = formatNumber(value ?? null, precision);
  return (
    <div className="flex items-start justify-between gap-3 py-1.5">
      <span className="text-sm text-muted">{label}</span>
      <span className="text-right">
        {n === null ? (
          <UnavailableValue kind={missingKind} why={why} action={action} inline />
        ) : (
          <span
            className={
              emphasis
                ? 'inline-flex items-baseline gap-1.5 font-mono text-base font-semibold text-modeled'
                : 'inline-flex items-baseline gap-1.5 font-mono text-sm text-ink'
            }
          >
            {n}
            {unit ? <span className="text-xs text-muted">{unit}</span> : null}
            {provenance ? <ProvenanceDot provenance={provenance} /> : null}
          </span>
        )}
      </span>
    </div>
  );
}
