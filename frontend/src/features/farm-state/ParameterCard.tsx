import { useMemo, useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { AnalysisParameter, SensorObservation, TomatoReferenceProfile } from '@/api/types';
import { variableByField } from '@/lib/variables';
import { formatNumber } from '@/lib/format';
import { cn } from '@/lib/cn';
import { TrendBadge } from '@/components/status/TrendBadge';
import { DeviationChip } from '@/components/status/DeviationChip';
import { InfoTooltip } from '@/components/primitives/InfoTooltip';
import { Sparkline } from '@/components/primitives/Sparkline';
import { VariableTrendChart } from '@/components/charts/VariableTrendChart';
import { buildTrendSeries } from '@/components/charts/series';

export function ParameterCard({
  param,
  observations,
  reference,
  day,
}: {
  param: AnalysisParameter;
  observations: SensorObservation[] | undefined;
  reference: TomatoReferenceProfile[] | undefined;
  day: number;
}) {
  const [open, setOpen] = useState(false);
  const variable = variableByField(param.current.field);
  const unit = variable?.unit ?? param.icar.unit_suffix?.trim() ?? '';
  const precision = variable?.precision ?? 1;

  const series = useMemo(
    () => (variable ? buildTrendSeries(observations, reference, variable, day) : []),
    [variable, observations, reference, day],
  );
  const spark = series.slice(-24);

  return (
    <div className="card p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="flex items-center gap-1.5 font-sans text-sm font-medium text-ink">
            {variable?.plain ?? param.current.parameter}
            <InfoTooltip
              content={
                <span>
                  Field <code className="font-mono text-xs">{param.current.field}</code>. Current
                  value is the mean of {param.current.n_readings} reading(s) on day {param.current.day}.
                </span>
              }
              label={`About ${variable?.plain ?? param.current.parameter}`}
            />
          </p>
          <p className="mt-1 font-display text-2xl font-semibold text-ink">
            {formatNumber(param.current.value, precision) ?? '—'}
            {unit ? <span className="ml-1 font-sans text-sm text-muted">{unit}</span> : null}
          </p>
        </div>
        <Sparkline
          data={spark}
          ariaLabel={`${variable?.plain ?? param.current.parameter} trend, last ${spark.length} days`}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5">
        <TrendBadge
          direction={param.trend.direction}
          rate={param.trend.rate_per_day}
          rateUnit={param.trend.rate_unit}
        />
        <DeviationChip value={param.icar.signed_difference} unitSuffix={param.icar.unit_suffix} />
        {param.persistence.days > 0 && param.persistence.direction !== 'STABLE' ? (
          <span className="text-xs text-muted">
            {param.persistence.direction.toLowerCase()} {param.persistence.days}d
          </span>
        ) : null}
      </div>

      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="mt-3 inline-flex items-center gap-1 font-sans text-sm text-brand-700"
      >
        {open ? 'Hide' : 'Show'} trend chart
        <ChevronDown size={14} aria-hidden className={cn('transition-transform', open && 'rotate-180')} />
      </button>

      {open && variable ? (
        <div className="mt-3 border-t border-hairline pt-3">
          <VariableTrendChart data={series} variable={variable} currentDay={day} height={200} />
        </div>
      ) : null}
    </div>
  );
}
