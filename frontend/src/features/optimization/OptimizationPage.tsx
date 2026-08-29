import { Link } from 'react-router-dom';
import { Info, Settings2, Sprout } from 'lucide-react';
import { useRunContext } from '@/context/RunContext';
import { useOptimization } from '@/api/hooks/optimization';
import { useDecision } from '@/api/hooks/pipeline';
import { PageHeader } from '@/components/primitives/PageHeader';
import { DayOutOfRangeNotice } from '@/components/primitives/DayOutOfRangeNotice';
import { FunnelEcho } from '@/components/layout/FunnelEcho';
import { EmptyState, ErrorState, SkeletonCard } from '@/components/primitives/states';
import { PrototypeBanner } from '@/components/disclaimers/PrototypeBanner';
import { SampleDataTag } from '@/components/disclaimers/SampleDataTag';
import { LimitationsList } from '@/components/disclaimers/LimitationsList';
import { ProvenanceLegend } from '@/components/status/Provenance';
import { WaterOptimizationCard } from './WaterOptimizationCard';
import { NutrientOptimizationCard } from './NutrientOptimizationCard';
import { UnsupportedActionCard } from './UnsupportedActionCard';

export function OptimizationPage() {
  const { runId, day, dayOutOfRange, durationDays } = useRunContext();
  const optimization = useOptimization(runId, dayOutOfRange ? null : day);
  const decision = useDecision({ runId, day, enabled: !dayOutOfRange });

  const data = optimization.data;
  const nothing =
    data != null &&
    data.water_optimizations.length === 0 &&
    data.nutrient_optimizations.length === 0 &&
    data.unsupported.length === 0;

  return (
    <>
      <FunnelEcho />
      <PageHeader
        eyebrow="4 · Optimized Plan"
        title="A quantity for the recommended action"
        lead="For water and nutrient actions only. Everything here is a KAVACH prototype figure with visible provenance."
        actions={<SampleDataTag />}
      />

      <PrototypeBanner />

      {dayOutOfRange ? (
        <DayOutOfRangeNotice max={durationDays} />
      ) : optimization.isLoading ? (
        <SkeletonCard lines={8} />
      ) : optimization.isError ? (
        <ErrorState error={optimization.error} onRetry={() => optimization.refetch()} />
      ) : data ? (
        <>
          {!data.farm_configuration.exists ? (
            <div className="mb-6 flex flex-col gap-3 rounded-lg border border-brand-700/30 bg-brand-tint/40 p-5 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="font-sans font-medium text-ink">Your farm isn't configured yet.</p>
                <p className="mt-0.5 text-sm text-body">
                  Whole-field totals, feasibility and cost stay unavailable until you set at least
                  field area.
                </p>
              </div>
              <Link
                to={`/runs/${runId}/farm-config?day=${day}`}
                className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded bg-brand-700 px-4 font-sans font-medium text-white hover:brightness-110"
              >
                <Settings2 size={16} aria-hidden /> Set up the farm
              </Link>
            </div>
          ) : (
            <div className="mb-6 flex items-center justify-between gap-3 rounded-lg border border-hairline bg-surface px-4 py-3 text-sm">
              <span className="text-muted">
                Farm: {data.farm_configuration.field_area}{' '}
                {data.farm_configuration.field_area_unit === 'm2'
                  ? 'm²'
                  : data.farm_configuration.field_area_unit}
                {data.farm_configuration.plant_population != null
                  ? ` · ${data.farm_configuration.plant_population} plants`
                  : ' · population not set'}
              </span>
              <Link
                to={`/runs/${runId}/farm-config?day=${day}`}
                className="inline-flex items-center gap-1.5 font-sans font-medium text-brand-700"
              >
                <Settings2 size={14} aria-hidden /> Edit
              </Link>
            </div>
          )}

          {data.multi_action_note ? (
            <p className="mb-6 flex items-start gap-2 rounded-lg border border-hairline bg-surface-sunken/60 px-4 py-3 text-sm text-body">
              <Info size={15} aria-hidden className="mt-0.5 shrink-0 text-muted" />
              {data.multi_action_note}
            </p>
          ) : null}

          {nothing ? (
            <EmptyState
              icon={<Sprout size={28} aria-hidden />}
              title={`Nothing to optimize on day ${day}.`}
              hint="No water or nutrient action is recommended, and no qualitative-only action applies."
            />
          ) : (
            <div className="space-y-6">
              {data.water_optimizations.map((o) => (
                <WaterOptimizationCard key={`w-${o.category}`} opt={o} runId={runId} day={day} />
              ))}
              {data.nutrient_optimizations.map((o) => (
                <NutrientOptimizationCard
                  key={`n-${o.category}-${o.nutrient}`}
                  opt={o}
                  runId={runId}
                  day={day}
                />
              ))}
              {data.unsupported.map((u) => (
                <UnsupportedActionCard
                  key={`u-${u.category}`}
                  item={u}
                  decision={decision.data?.decisions.find((d) => d.category === u.category)}
                />
              ))}
            </div>
          )}

          <LimitationsList items={data.limitations} className="mt-8" />

          <details className="mt-6 rounded-lg border border-hairline bg-surface p-4">
            <summary className="cursor-pointer font-sans text-sm font-medium text-ink">
              What do the provenance dots mean?
            </summary>
            <div className="mt-3">
              <ProvenanceLegend />
              <p className="mt-3 text-xs text-muted">
                Full explanation on the <Link to="/about" className="text-brand-700 underline">Legend</Link>{' '}
                page.
              </p>
            </div>
          </details>
        </>
      ) : null}
    </>
  );
}
