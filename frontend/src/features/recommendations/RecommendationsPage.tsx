import { useState } from 'react';
import type { ReactNode } from 'react';
import { ClipboardCheck } from 'lucide-react';
import type { DecisionRecord, ProblemCategory } from '@/api/types';
import { useRunContext } from '@/context/RunContext';
import { useDecision } from '@/api/hooks/pipeline';
import { PageHeader } from '@/components/primitives/PageHeader';
import { BridgeCard } from '@/components/primitives/BridgeCard';
import { DayOutOfRangeNotice } from '@/components/primitives/DayOutOfRangeNotice';
import { FunnelEcho } from '@/components/layout/FunnelEcho';
import { EmptyState, ErrorState, SkeletonGrid } from '@/components/primitives/states';
import { ReasoningPanel } from '@/components/why/ReasoningPanel';
import { RecommendationCard } from './RecommendationCard';

export function RecommendationsPage() {
  const { runId, day, dayOutOfRange, durationDays } = useRunContext();
  const decision = useDecision({ runId, day, enabled: !dayOutOfRange });
  const [whyCategory, setWhyCategory] = useState<ProblemCategory | null>(null);

  const decisions = decision.data?.decisions ?? [];
  const recommended = decisions
    .filter((d) => d.outcome === 'ACTION_RECOMMENDED')
    .sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99));
  const monitor = decisions.filter((d) => d.outcome === 'MONITOR');
  const conflict = decisions.filter((d) => d.outcome === 'CONFLICT');
  const inactive = decisions.filter(
    (d) => d.outcome === 'NO_ACTION' || d.outcome === 'INSUFFICIENT_SUPPORT',
  );

  const renderCards = (list: DecisionRecord[]) => (
    <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
      {list.map((d) => (
        <RecommendationCard
          key={d.category}
          record={d}
          runId={runId}
          day={day}
          onWhy={() => setWhyCategory(d.category)}
        />
      ))}
    </div>
  );

  return (
    <>
      <FunnelEcho />
      <PageHeader
        eyebrow="3 · Recommendations"
        title="The smallest justified action"
        lead="An evidenced problem only becomes a recommendation after it clears every eligibility check."
      />

      {dayOutOfRange ? (
        <DayOutOfRangeNotice max={durationDays} />
      ) : decision.isLoading ? (
        <SkeletonGrid count={3} />
      ) : decision.isError ? (
        <ErrorState error={decision.error} onRetry={() => decision.refetch()} />
      ) : recommended.length === 0 ? (
        <>
          <EmptyState
            icon={<ClipboardCheck size={28} aria-hidden />}
            title={`No action recommended for day ${day}.`}
            hint="Nothing cleared the eligibility bar. Categories being watched or in conflict are listed below."
          />
          <SecondarySections
            monitor={monitor}
            conflict={conflict}
            inactive={inactive}
            render={renderCards}
          />
        </>
      ) : (
        <>
          {renderCards(recommended)}
          <SecondarySections
            monitor={monitor}
            conflict={conflict}
            inactive={inactive}
            render={renderCards}
          />
          <BridgeCard
            meaning="For water and nutrient actions, KAVACH can propose a quantity — with its provenance and limits."
            to={`/runs/${runId}/optimization?day=${day}`}
            cta="See the optimized plan"
          />
        </>
      )}

      {whyCategory ? (
        <ReasoningPanel
          open={whyCategory != null}
          onOpenChange={(v) => !v && setWhyCategory(null)}
          category={whyCategory}
          runId={runId}
          day={day}
        />
      ) : null}
    </>
  );
}

function CollapsedSection({
  title,
  list,
  render,
}: {
  title: string;
  list: DecisionRecord[];
  render: (list: DecisionRecord[]) => ReactNode;
}) {
  if (!list.length) return null;
  return (
    <details className="mt-6 rounded-lg border border-hairline bg-surface p-4">
      <summary className="cursor-pointer font-sans text-sm font-medium text-ink">
        {title} ({list.length})
      </summary>
      <div className="mt-4">{render(list)}</div>
    </details>
  );
}

function SecondarySections({
  monitor,
  conflict,
  inactive,
  render,
}: {
  monitor: DecisionRecord[];
  conflict: DecisionRecord[];
  inactive: DecisionRecord[];
  render: (list: DecisionRecord[]) => ReactNode;
}) {
  return (
    <>
      <CollapsedSection title="Keep watching" list={monitor} render={render} />
      <CollapsedSection title="Conflicting signals" list={conflict} render={render} />
      <CollapsedSection title="No action / not enough support" list={inactive} render={render} />
    </>
  );
}
