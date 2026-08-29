import { Link } from 'react-router-dom';
import { FlaskRound } from 'lucide-react';
import type { NutrientOptimization } from '@/api/types';
import { CATEGORY, POPULATION_SOURCE } from '@/lib/plain-language';
import { formatNumber } from '@/lib/format';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { ProvenanceDot } from '@/components/status/Provenance';
import { UnavailableValue } from '@/components/status/UnavailableValue';
import { LimitationsList } from '@/components/disclaimers/LimitationsList';
import { QuantityRow } from './QuantityRow';

const NUTRIENT_LABEL: Record<string, string> = { N: 'Nitrogen', P2O5: 'Phosphorus (P₂O₅)', K2O: 'Potassium (K₂O)' };

export function NutrientOptimizationCard({
  opt,
  runId,
  day,
}: {
  opt: NutrientOptimization;
  runId: number;
  day: number;
}) {
  const cat = CATEGORY[opt.category] ?? { plain: opt.action_label };
  const popUnknown = opt.plant_population.source === 'UNKNOWN';
  const firstLimit = opt.limitations[0];

  return (
    <article className="card p-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-2 font-sans text-xs font-semibold uppercase tracking-wide text-modeled">
            <FlaskRound size={14} aria-hidden /> Nutrient · More {NUTRIENT_LABEL[opt.nutrient] ?? opt.nutrient}
          </p>
          <h3 className="mt-1 font-sans text-lg font-semibold text-ink">{cat.plain}</h3>
          <p className="mt-0.5 text-xs text-muted">{opt.direction_basis}</p>
        </div>
        <SeverityBadge severity={opt.severity} />
      </header>

      <section className="mt-5">
        <h4 className="mb-1 font-sans text-sm font-semibold text-ink">Per plant, per day</h4>
        <QuantityRow
          label="Baseline (ICAR demand)"
          value={opt.baseline_g_per_plant_day}
          unit="g"
          provenance={opt.baseline_provenance}
          why={firstLimit}
        />
        <QuantityRow
          label="Adjustment"
          value={opt.adjustment_pct}
          unit="%"
          provenance={opt.adjustment_provenance}
          precision={0}
        />
        <QuantityRow
          label="Optimized"
          value={opt.optimized_g_per_plant_day}
          unit="g"
          provenance={opt.optimized_provenance}
          why={firstLimit}
          emphasis
        />
      </section>

      <section className="mt-5 border-t border-hairline pt-4">
        <h4 className="mb-1 font-sans text-sm font-semibold text-ink">Whole field</h4>
        <div className="mb-2 text-xs text-muted">
          Plant population:{' '}
          {popUnknown ? (
            <>
              <UnavailableValue kind="unknown" inline why={opt.plant_population.note} />{' '}
              <Link
                to={`/runs/${runId}/farm-config?day=${day}`}
                className="font-medium text-brand-700 underline"
              >
                Set plant population
              </Link>
            </>
          ) : (
            <>
              <span className="font-mono text-body">{formatNumber(opt.plant_population.plants, 0)}</span> —{' '}
              {POPULATION_SOURCE[opt.plant_population.source].plain}
            </>
          )}
        </div>
        <QuantityRow
          label="Baseline total"
          value={opt.baseline_total_kg_per_day}
          unit="kg/day"
          provenance="MODELED"
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
        />
        <QuantityRow
          label="Optimized total"
          value={opt.total_kg_per_day}
          unit="kg/day"
          provenance="MODELED"
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
          emphasis
        />
        <QuantityRow
          label={`Over ${opt.duration_days ?? '—'} days`}
          value={opt.total_quantity_kg}
          unit="kg"
          provenance={opt.duration_provenance}
          missingKind={popUnknown ? 'unknown' : 'unavailable'}
        />
      </section>

      <section className="mt-5 border-t border-hairline pt-4">
        <h4 className="mb-2 font-sans text-sm font-semibold text-ink">Cost</h4>
        {opt.cost.status === 'UNAVAILABLE' ? (
          <UnavailableValue kind="unavailable" why={opt.cost.detail} />
        ) : (
          <>
            <QuantityRow label="Baseline cost" value={opt.cost.baseline_cost} provenance="MODELED" />
            <QuantityRow label="Optimized cost" value={opt.cost.optimized_cost} provenance="MODELED" />
            <QuantityRow label="Change" value={opt.cost.cost_change} provenance="MODELED" emphasis />
          </>
        )}
      </section>

      <section className="mt-5 border-t border-hairline pt-4 text-sm">
        <span className="font-sans font-medium text-ink">Expected direction: </span>
        {opt.expected_direction} <ProvenanceDot provenance={opt.expected_direction_basis} />
      </section>

      {opt.limitations.length ? (
        <LimitationsList items={opt.limitations} title="Notes for this optimization" className="mt-5" />
      ) : null}
    </article>
  );
}
