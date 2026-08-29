import { useRunContext } from '@/context/RunContext';
import { useAnalysis, useObservations } from '@/api/hooks/pipeline';
import { useReferenceProfile } from '@/api/hooks/reference';
import { PageHeader } from '@/components/primitives/PageHeader';
import { BridgeCard } from '@/components/primitives/BridgeCard';
import { DayOutOfRangeNotice } from '@/components/primitives/DayOutOfRangeNotice';
import { FunnelEcho } from '@/components/layout/FunnelEcho';
import { ErrorState, SkeletonGrid, SkeletonCard } from '@/components/primitives/states';
import { StateSummary } from './StateSummary';
import { HeadlineMetrics } from './HeadlineMetrics';
import { ParameterCard } from './ParameterCard';

export function FarmStatePage() {
  const { runId, day, dayOutOfRange, durationDays } = useRunContext();
  const analysis = useAnalysis({ runId, day, enabled: !dayOutOfRange });
  const observations = useObservations({ runId, day: null, enabled: !dayOutOfRange });
  const reference = useReferenceProfile();

  return (
    <>
      <FunnelEcho />
      <PageHeader
        eyebrow="1 · Farm State"
        title="What the sensors show"
        lead="Each variable's current value, trend, persistence and distance from the ICAR reference for the selected day."
      />

      {dayOutOfRange ? (
        <DayOutOfRangeNotice max={durationDays} />
      ) : analysis.isLoading ? (
        <>
          <SkeletonCard className="mb-8" lines={2} />
          <SkeletonGrid count={7} />
        </>
      ) : analysis.isError ? (
        <ErrorState error={analysis.error} onRetry={() => analysis.refetch()} />
      ) : analysis.data ? (
        <>
          <StateSummary analysis={analysis.data} />
          <HeadlineMetrics parameters={analysis.data.parameters} />

          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {analysis.data.parameters.map((p) => (
              <ParameterCard
                key={p.current.field}
                param={p}
                observations={observations.data}
                reference={reference.data}
                day={day}
              />
            ))}
          </div>

          {analysis.data.data_quality_notes.length > 0 && (
            <div className="mt-6 flex flex-wrap gap-2">
              {analysis.data.data_quality_notes.map((n, i) => (
                <span
                  key={i}
                  className="rounded-pill border border-hairline bg-surface-sunken px-3 py-1 text-xs text-muted"
                >
                  {n}
                </span>
              ))}
            </div>
          )}

          <BridgeCard
            meaning="These readings are just observations — the next step decides which of them count as a problem."
            to={`/runs/${runId}/problems?day=${day}`}
            cta="See detected problems"
          />
        </>
      ) : null}
    </>
  );
}
