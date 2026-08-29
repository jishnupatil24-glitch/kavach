import { useState } from 'react';
import { CheckCircle2 } from 'lucide-react';
import type { ProblemCategory } from '@/api/types';
import { useRunContext } from '@/context/RunContext';
import { useAssessment } from '@/api/hooks/pipeline';
import { PageHeader } from '@/components/primitives/PageHeader';
import { BridgeCard } from '@/components/primitives/BridgeCard';
import { DayOutOfRangeNotice } from '@/components/primitives/DayOutOfRangeNotice';
import { FunnelEcho } from '@/components/layout/FunnelEcho';
import { SegmentedToggle } from '@/components/primitives/SegmentedToggle';
import { EmptyState, ErrorState, SkeletonGrid } from '@/components/primitives/states';
import { ReasoningPanel } from '@/components/why/ReasoningPanel';
import { ProblemCard } from './ProblemCard';

type View = 'matter' | 'all';

export function ProblemsPage() {
  const { runId, day, dayOutOfRange, durationDays } = useRunContext();
  const assessment = useAssessment({ runId, day, enabled: !dayOutOfRange });
  const [view, setView] = useState<View>('matter');
  const [whyCategory, setWhyCategory] = useState<ProblemCategory | null>(null);

  const problems = assessment.data?.problems ?? [];
  const mattering = problems.filter(
    (p) => p.status === 'weak_evidence' || p.status === 'corroborated_evidence',
  );
  const shown = view === 'matter' ? mattering : problems;

  return (
    <>
      <FunnelEcho />
      <PageHeader
        eyebrow="2 · Problems"
        title="Which readings count as a problem"
        lead="Every category carries two independent things: how sure KAVACH is (evidence) and how bad it looks (severity)."
        actions={
          <SegmentedToggle
            ariaLabel="Problem view"
            value={view}
            onChange={(v) => setView(v)}
            options={[
              { value: 'matter', label: 'Problems that matter' },
              { value: 'all', label: 'All 10 categories' },
            ]}
          />
        }
      />

      {dayOutOfRange ? (
        <DayOutOfRangeNotice max={durationDays} />
      ) : assessment.isLoading ? (
        <SkeletonGrid count={4} />
      ) : assessment.isError ? (
        <ErrorState error={assessment.error} onRetry={() => assessment.refetch()} />
      ) : view === 'matter' && mattering.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 size={28} aria-hidden className="text-feas-pass" />}
          title={`No problems detected on day ${day}.`}
          hint="No category reached weak or corroborated evidence. The other categories are still listed under “All 10 categories”."
          action={
            <button
              type="button"
              className="font-sans text-sm text-brand-700"
              onClick={() => setView('all')}
            >
              Show all 10 categories
            </button>
          }
        />
      ) : (
        <>
          <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
            {shown.map((p) => (
              <ProblemCard key={p.category} problem={p} onWhy={() => setWhyCategory(p.category)} />
            ))}
          </div>
          <BridgeCard
            meaning="Evidence and severity don't decide anything on their own — the decision engine gates them next."
            to={`/runs/${runId}/recommendations?day=${day}`}
            cta="See recommendations"
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
