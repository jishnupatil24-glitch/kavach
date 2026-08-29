import { Link } from 'react-router-dom';
import { HelpCircle } from 'lucide-react';
import type { DecisionRecord } from '@/api/types';
import { CATEGORY } from '@/lib/plain-language';
import { EvidenceIndicator } from '@/components/status/EvidenceIndicator';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { OutcomeBadge } from '@/components/status/OutcomeBadge';
import { EligibilityChecklist } from '@/components/status/EligibilityCheck';
import { Button } from '@/components/primitives/Button';

export function RecommendationCard({
  record,
  runId,
  day,
  onWhy,
}: {
  record: DecisionRecord;
  runId: number;
  day: number;
  onWhy: () => void;
}) {
  const cat = CATEGORY[record.category] ?? { plain: record.label };
  const recommended = record.outcome === 'ACTION_RECOMMENDED';

  return (
    <article className="card p-5">
      <header className="flex items-start justify-between gap-3">
        <div>
          {record.priority != null ? (
            <span className="font-sans text-xs font-semibold uppercase tracking-wide text-brand-700">
              Priority #{record.priority}
            </span>
          ) : null}
          <h3 className="mt-0.5 font-sans text-base font-semibold text-ink">
            {recommended && record.action_label ? record.action_label : cat.plain}
          </h3>
          <p className="mt-0.5 text-xs text-muted">
            {cat.plain} · <code className="font-mono">{record.category}</code>
          </p>
        </div>
        <OutcomeBadge outcome={record.outcome} priority={record.priority} />
      </header>

      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-2">
        <EvidenceIndicator status={record.status} />
        <SeverityBadge severity={record.severity} />
      </div>

      {record.conflict_with ? (
        <p className="mt-3 rounded border border-sev-high/40 bg-sev-high/5 px-3 py-2 text-sm text-body">
          Conflicts with{' '}
          <span className="font-medium text-ink">
            {CATEGORY[record.conflict_with]?.plain ?? record.conflict_with}
          </span>{' '}
          — an opposite-direction problem on the same measurement. KAVACH will not act on either.
        </p>
      ) : null}

      <div className="mt-4">
        <p className="mb-1 font-sans text-sm font-medium text-ink">Eligibility checks</p>
        <EligibilityChecklist checks={record.eligibility_checks} />
      </div>

      {record.priority_reason ? (
        <p className="mt-3 text-xs text-muted">{record.priority_reason}</p>
      ) : null}

      {recommended ? (
        <p className="mt-3 rounded bg-brand-tint/50 px-3 py-2 text-sm text-body">
          Quantities are calculated in the next step.{' '}
          <Link
            to={`/runs/${runId}/optimization?day=${day}`}
            className="font-medium text-brand-700 underline"
          >
            Open the optimized plan
          </Link>
          .
        </p>
      ) : null}

      <div className="mt-4">
        <Button size="sm" variant="secondary" onClick={onWhy} className="w-full">
          <HelpCircle size={14} aria-hidden />
          Why did KAVACH say this?
        </Button>
      </div>
    </article>
  );
}
