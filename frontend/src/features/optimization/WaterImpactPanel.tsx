import { Link } from 'react-router-dom';
import { Droplet, ArrowDown } from 'lucide-react';
import type { WaterOptimization } from '@/api/types';
import { formatNumber, formatPercent, isMissing } from '@/lib/format';
import { classifyWaterImpact } from '@/lib/waterImpact';
import { ProvenanceDot } from '@/components/status/Provenance';
import { UnavailableValue } from '@/components/status/UnavailableValue';

/**
 * The PRIMARY farmer-facing water metric: typical (over-)application vs
 * KAVACH's recommendation. Deliberately separate from the theoretical
 * crop-requirement comparison (see QuantityRow/SavingsPanel below it on the
 * card) so the two are never visually confused — per-plant "theoretical
 * requirement" is a modelling input, this is the farmer decision story.
 */
export function WaterImpactPanel({
  opt,
  runId,
  day,
}: {
  opt: WaterOptimization;
  runId: number;
  day: number;
}) {
  const havePopulation = opt.plant_population.source !== 'UNKNOWN';

  const typicalValue = havePopulation ? opt.typical_l_per_day : opt.typical_l_per_plant_day;
  const kavachValue = havePopulation ? opt.optimized_l_per_day : opt.optimized_l_per_plant_day;
  const unit = havePopulation ? 'L/day' : 'L/plant/day';

  const impact = classifyWaterImpact(
    havePopulation ? opt.water_saved_vs_typical_l_per_day : null,
    havePopulation ? opt.water_saved_vs_typical_percentage : null,
  );

  const totalMagnitude =
    havePopulation && opt.total_water_saved_vs_typical_liters != null
      ? Math.abs(opt.total_water_saved_vs_typical_liters)
      : null;

  return (
    <div className="rounded-lg border border-hairline bg-surface p-5">
      <p className="flex items-center gap-2 font-sans text-xs font-semibold uppercase tracking-wide text-muted">
        <Droplet size={14} aria-hidden /> Water impact — vs typical application
      </p>

      {!havePopulation ? (
        <p className="mt-2 text-xs text-muted">
          Whole-field figures need plant population.{' '}
          <Link to={`/runs/${runId}/farm-config?day=${day}`} className="font-medium text-brand-700 underline">
            Set it in Farm Setup
          </Link>
          . Showing per-plant figures for now.
        </p>
      ) : null}

      <div className="mt-4 grid grid-cols-1 items-center gap-4 sm:grid-cols-[1fr_auto_1fr]">
        <div>
          <p className="font-sans text-sm text-muted">Typical application</p>
          <p className="mt-1 font-mono text-2xl font-semibold text-ink">
            {isMissing(typicalValue) ? (
              <UnavailableValue kind="unavailable" inline why={opt.limitations[0]} />
            ) : (
              <>
                {formatNumber(typicalValue, 0)} <span className="text-base font-normal text-muted">{unit}</span>
              </>
            )}
          </p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-muted">
            <ProvenanceDot provenance={opt.typical_provenance} /> Modelled — not measured farmer data
            {opt.typical_application_multiplier_pct != null
              ? ` (+${formatNumber(opt.typical_application_multiplier_pct, 0)}% over theoretical requirement, prototype assumption)`
              : ''}
          </p>
        </div>

        <ArrowDown className="mx-auto rotate-0 text-muted sm:-rotate-90" size={20} aria-hidden />

        <div>
          <p className="font-sans text-sm text-muted">KAVACH recommendation</p>
          <p className="mt-1 font-mono text-2xl font-semibold text-modeled">
            {isMissing(kavachValue) ? (
              <UnavailableValue kind="unavailable" inline why={opt.limitations[0]} />
            ) : (
              <>
                {formatNumber(kavachValue, 0)} <span className="text-base font-normal text-muted">{unit}</span>
              </>
            )}
          </p>
          <p className="mt-0.5 flex items-center gap-1 text-xs text-muted">
            <ProvenanceDot provenance={opt.optimized_provenance} /> Calculated by KAVACH
          </p>
        </div>
      </div>

      <div className="mt-5 border-t border-hairline pt-4">
        {impact.kind === 'unavailable' ? (
          <UnavailableValue
            kind={havePopulation ? 'unavailable' : 'unknown'}
            why={
              havePopulation
                ? 'Typical application or KAVACH recommendation is unavailable, so the comparison cannot be computed.'
                : 'Plant population is unknown, so the whole-field comparison cannot be computed.'
            }
          />
        ) : impact.kind === 'equal' ? (
          <p className="font-sans text-base font-medium text-body">
            KAVACH's recommendation matches typical application — 0 {unit} difference.
          </p>
        ) : (
          <>
            <p className="font-sans text-sm font-medium text-body">
              {impact.kind === 'saved' ? 'Water saved vs typical application' : 'Additional water required vs typical application'}
            </p>
            <p
              className={
                'mt-1 font-display text-3xl font-semibold ' +
                (impact.kind === 'saved' ? 'text-feas-pass' : 'text-sev-high')
              }
            >
              {formatNumber(impact.magnitudePerDay, 0)} {unit}
              {impact.magnitudePct != null ? (
                <span className="ml-2 text-lg font-sans font-medium">({formatPercent(impact.magnitudePct)})</span>
              ) : null}
            </p>
            {totalMagnitude != null ? (
              <p className="mt-1 text-sm text-body">
                {formatNumber(totalMagnitude, 0)} L {impact.kind === 'saved' ? 'saved' : 'more needed'} over the{' '}
                {opt.review_cycle_days ?? '—'}-day review cycle
              </p>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}
