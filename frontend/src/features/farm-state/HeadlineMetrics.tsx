import type { AnalysisParameter } from '@/api/types';
import { VARIABLES, variableByField } from '@/lib/variables';
import { formatNumber } from '@/lib/format';
import { TrendBadge } from '@/components/status/TrendBadge';
import { DeviationChip } from '@/components/status/DeviationChip';

/** The three at-a-glance readings: soil moisture, temperature, humidity. */
export function HeadlineMetrics({ parameters }: { parameters: AnalysisParameter[] }) {
  const headlineKeys = VARIABLES.filter((v) => v.headline).map((v) => v.key);
  const cards = headlineKeys
    .map((k) => parameters.find((p) => p.current.field === k || p.current.parameter === k))
    .filter((p): p is AnalysisParameter => Boolean(p));

  if (!cards.length) return null;

  return (
    <div className="mb-8 grid gap-4 sm:grid-cols-3">
      {cards.map((p) => {
        const v = variableByField(p.current.field);
        return (
          <div key={p.current.field} className="card p-5">
            <p className="font-sans text-sm font-medium text-muted">{v?.plain ?? p.current.parameter}</p>
            <p className="mt-1 font-display text-3xl font-semibold text-ink">
              {formatNumber(p.current.value, v?.precision ?? 1) ?? '—'}
              <span className="ml-1 font-sans text-base text-muted">{v?.unit ?? ''}</span>
            </p>
            <div className="mt-3 flex flex-col gap-1.5">
              <TrendBadge
                direction={p.trend.direction}
                rate={p.trend.rate_per_day}
                rateUnit={p.trend.rate_unit}
              />
              <DeviationChip value={p.icar.signed_difference} unitSuffix={p.icar.unit_suffix} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
