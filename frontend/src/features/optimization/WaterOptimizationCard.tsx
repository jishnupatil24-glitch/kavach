import { Link } from 'react-router-dom';
import { Droplets } from 'lucide-react';
import type { WaterOptimization } from '@/api/types';
import { CATEGORY, POPULATION_SOURCE } from '@/lib/plain-language';
import { formatNumber } from '@/lib/format';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { FeasibilityPill } from '@/components/status/FeasibilityPill';
import { ProvenanceDot } from '@/components/status/Provenance';
import { UnavailableValue } from '@/components/status/UnavailableValue';
import { LimitationsList } from '@/components/disclaimers/LimitationsList';
import { QuantityRow } from './QuantityRow';
import { SavingsPanel } from './SavingsPanel';

export function WaterOptimizationCard({
  opt,
  runId,
  day,
}: {
  opt: WaterOptimization;
  runId: number;
  day: number;
}) {
  const cat = CATEGORY[opt.category] ?? { plain: opt.action_label };
  const dirWord = opt.direction === 'increase' ? 'More water' : 'Less water';
  const popUnknown = opt.plant_population.source === 'UNKNOWN';
  const firstLimit = opt.limitations[0];

  return (
    <article className="card p-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-sans text-xs font-semibold uppercase tracking-wide text-modeled">
            <Droplets size={14} aria-hidden /> Water · {dirWord}
          </p>
          <h3 className="mt-1 font-sans text-lg font-semibold text-ink">{cat.plain}</h3>
          <p className="mt-0.5 text-xs text-muted">
            {opt.stage_name ? `Stage: ${opt.stage_name.replace(/_/g, ' ')}` : 'No baseline for this stage'}
          </p>
        </div>
        <SeverityBadge severity={opt.severity} />
      </header>

      {/* Per plant */}
      <section className="mt-5">
        <h4 className="mb-1 font-sans text-sm font-semibold text-ink">Per plant, per day</h4>
        <QuantityRow
          label="Baseline"
          value={opt.baseline_l_per_plant_day}
          unit="L"
          provenance={opt.baseline_provenance}
          why={firstLimit}
        />
        <QuantityRow
          label={`Adjustment (${opt.direction})`}
          value={opt.adjustment_pct}
          unit="%"
          provenance={opt.adjustment_provenance}
          precision={0}
        />
        <QuantityRow
          label="Optimized"
          value={opt.optimized_l_per_plant_day}
          unit="L"
          provenance={opt.optimized_provenance}
          why={firstLimit}
          emphasis
        />
      </section>

      {/* Whole field */}
      <section className="mt-5 border-t border-hairline pt-4">
        <h4 className="mb-1 font-sans text-sm font-semibold text-ink">Whole field, per day</h4>
        <div className="mb-2 text-xs text-muted">
          Plant population:{' '}
          {popUnknown ? (
            <UnavailableValue
              kind="unknown"
              inline
              why={opt.plant_population.note}
            />
          ) : (
            <>
              <span className="font-mono text-body">
                {formatNumber(opt.plant_population.plants, 0)}
              </span>{' '}
              — {POPULATION_SOURCE[opt.plant_population.source].plain}
            </>
          )}
          {popUnknown ? (
            <>
              {' '}
              <Link
                to={`/runs/${runId}/farm-config?day=${day}`}
                className="font-medium text-brand-700 underline"
              >
                Set plant population
              </Link>
            </>
          ) : null}
        </div>
        <QuantityRow
          label="Baseline"
          value={opt.baseline_l_per_day}
          unit="L/day"
          provenance="MODELED"
          precision={0}
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
          why={firstLimit}
        />
        <QuantityRow
          label="Optimized"
          value={opt.optimized_l_per_day}
          unit="L/day"
          provenance="MODELED"
          precision={0}
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
          why={firstLimit}
          emphasis
        />
        <div className="mt-3">
          <SavingsPanel
            savedPerDay={opt.water_saved_l_per_day}
            savingPct={opt.water_saving_percentage}
            totalSaved={opt.total_water_saved_liters}
            reviewCycleDays={opt.review_cycle_days}
            why={firstLimit}
          />
        </div>
      </section>

      {/* Delivered + feasibility */}
      <section className="mt-5 border-t border-hairline pt-4">
        <h4 className="mb-2 font-sans text-sm font-semibold text-ink">
          Delivered volume &amp; feasibility
        </h4>
        <p className="mb-2 text-xs text-muted">
          Irrigation efficiency {opt.irrigation_efficiency_pct ?? '—'}%
          {opt.irrigation_efficiency_source ? ` (${opt.irrigation_efficiency_source})` : ''} —
          delivered figures account for it.
        </p>
        <QuantityRow
          label="Delivered baseline"
          value={opt.delivered_baseline_l_per_day}
          unit="L/day"
          provenance="MODELED"
          precision={0}
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
        />
        <QuantityRow
          label="Delivered optimized"
          value={opt.delivered_optimized_l_per_day}
          unit="L/day"
          provenance="MODELED"
          precision={0}
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
        />
        <div className="mt-3 flex flex-wrap gap-2">
          {opt.feasibility.map((f) => (
            <FeasibilityPill key={f.label} status={f.status} label={f.label} />
          ))}
        </div>
        {opt.feasibility.map((f) => (
          <p key={f.label} className="mt-1 text-xs text-muted">
            {f.detail}
          </p>
        ))}
      </section>

      {/* Cost */}
      <section className="mt-5 border-t border-hairline pt-4">
        <h4 className="mb-2 font-sans text-sm font-semibold text-ink">Cost</h4>
        {opt.cost.status === 'UNAVAILABLE' ? (
          <UnavailableValue kind="unavailable" why={opt.cost.detail} />
        ) : (
          <>
            <QuantityRow label="Baseline cost" value={opt.cost.baseline_cost} provenance="MODELED" />
            <QuantityRow label="Optimized cost" value={opt.cost.optimized_cost} provenance="MODELED" />
            <QuantityRow
              label="Change"
              value={opt.cost.cost_change}
              provenance="MODELED"
              emphasis
            />
            <p className="mt-1 text-xs text-muted">
              {opt.cost.detail} Negative = a saving; positive = more expensive.
            </p>
          </>
        )}
      </section>

      <section className="mt-5 border-t border-hairline pt-4 text-sm">
        <span className="font-sans font-medium text-ink">Expected direction: </span>
        {opt.expected_direction}{' '}
        <ProvenanceDot provenance={opt.expected_direction_basis} />
      </section>

      {opt.limitations.length ? (
        <LimitationsList items={opt.limitations} title="Notes for this optimization" className="mt-5" />
      ) : null}
    </article>
  );
}
