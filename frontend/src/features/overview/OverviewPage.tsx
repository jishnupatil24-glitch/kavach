import { useRunContext } from '@/context/RunContext';
import { useAnalysis } from '@/api/hooks/pipeline';
import { runLabel } from '@/features/runs/runLabel';
import { formatNumber, formatPercent } from '@/lib/format';
import { PageHeader } from '@/components/primitives/PageHeader';
import { DayScrubber } from '@/components/layout/DayScrubber';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { SampleDataTag } from '@/components/disclaimers/SampleDataTag';
import { ErrorState } from '@/components/primitives/states';
import { DayOutOfRangeNotice } from '@/components/primitives/DayOutOfRangeNotice';
import { StageTile } from './StageTile';
import { useFunnelSummary } from './useFunnelSummary';

export function OverviewPage() {
  const { runId, run, day, dayOutOfRange, durationDays } = useRunContext();
  const analysis = useAnalysis({ runId, day, enabled: !dayOutOfRange });
  const summary = useFunnelSummary(runId, dayOutOfRange ? null : day);

  if (dayOutOfRange) return <DayOutOfRangeNotice max={durationDays} />;

  const stages = analysis.data?.crop_stages ?? [];
  const stageText = stages.length
    ? stages.map((s) => s.name.replace(/_/g, ' ')).join(', ')
    : 'crop stage unavailable';

  const search = `?day=${day}`;
  const base = `/runs/${runId}`;

  return (
    <>
      <PageHeader
        eyebrow="Farm Command"
        title={run ? `Run #${run.id} — ${runLabel(run)}` : 'Farm Command'}
        lead="KAVACH watches this tomato polyhouse, finds problems, and recommends the smallest justified fix."
      />

      <p className="mb-8 text-sm text-muted">
        <span className="font-sans font-medium text-ink">
          Day {day} of {durationDays ?? '—'}
        </span>{' '}
        · {stageText}
      </p>

      {analysis.isError ? (
        <ErrorState error={analysis.error} onRetry={() => analysis.refetch()} className="mb-6" />
      ) : null}

      {/* The four connected stage tiles — the decision story, left to right. */}
      <div className="relative">
        <span
          aria-hidden
          className="pointer-events-none absolute left-6 right-6 top-9 hidden h-px bg-hairline lg:block"
        />
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          <StageTile
            index={1}
            label="Farm State"
            to={`${base}/state${search}`}
            loading={summary.isLoading}
            headline={summary.state.moving ?? '—'}
            headlineNote={`of ${summary.state.total} variables trending`}
            caption={
              summary.state.leadVariable
                ? `${summary.state.leadVariable} is moving fastest.`
                : 'Sensor readings vs the ICAR reference.'
            }
          />
          <StageTile
            index={2}
            label="Problems"
            to={`${base}/problems${search}`}
            loading={summary.isLoading}
            headline={summary.problems.count ?? '—'}
            headlineNote="with real evidence"
            caption={
              summary.problems.topCategory
                ? `Most serious: ${summary.problems.topCategory}.`
                : 'No corroborated problems today.'
            }
            badge={
              summary.problems.topSeverity ? (
                <SeverityBadge severity={summary.problems.topSeverity} />
              ) : undefined
            }
          />
          <StageTile
            index={3}
            label="Recommendations"
            to={`${base}/recommendations${search}`}
            loading={summary.isLoading}
            headline={summary.recommendations.count ?? '—'}
            headlineNote="actions recommended"
            caption={
              summary.recommendations.topActionLabel
                ? `Top priority: "${summary.recommendations.topActionLabel}".`
                : 'Nothing cleared the bar to act.'
            }
          />
          <StageTile
            index={4}
            label="Optimized Plan"
            to={`${base}/optimization${search}`}
            loading={summary.isLoading}
            accent="modeled"
            headline={summary.optimization.quantified ?? '—'}
            headlineNote="quantified — prototype"
            caption={
              summary.optimization.headlineImpactKind === 'saved' ||
              summary.optimization.headlineImpactKind === 'additional'
                ? `${formatNumber(summary.optimization.headlineImpactPerDay, 0)} L/day ${
                    summary.optimization.headlineImpactKind === 'saved' ? 'saved' : 'more needed'
                  } vs typical application${
                    summary.optimization.headlineImpactPct != null
                      ? ` (${formatPercent(summary.optimization.headlineImpactPct)})`
                      : ''
                  }.`
                : summary.optimization.anyUnsupported
                  ? 'Only qualitative actions apply today.'
                  : 'Nothing to quantify today.'
            }
            badge={<SampleDataTag />}
          />
        </div>
      </div>

      <div className="mt-10 flex flex-col gap-3 rounded-lg border border-hairline bg-surface p-5 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="font-sans text-sm font-medium text-ink">Move through the run</p>
          <p className="mt-0.5 text-sm text-muted">
            {summary.changeNote ?? 'Scrub the day to watch the story change.'}
          </p>
        </div>
        <DayScrubber />
      </div>
    </>
  );
}
