import { Info } from 'lucide-react';
import type { DecisionRecord, UnsupportedAction } from '@/api/types';
import { CATEGORY } from '@/lib/plain-language';
import { OutcomeBadge } from '@/components/status/OutcomeBadge';

/**
 * A category that is ACTION_RECOMMENDED but has no quantitative model
 * (heat / cold / humidity / light). Not an error — show Phase 5's qualitative
 * recommendation as-is with the reason as an explanatory note.
 */
export function UnsupportedActionCard({
  item,
  decision,
}: {
  item: UnsupportedAction;
  decision?: DecisionRecord;
}) {
  const cat = CATEGORY[item.category] ?? { plain: item.action_label };
  return (
    <article className="card p-6">
      <header className="flex items-start justify-between gap-3">
        <div>
          <p className="font-sans text-xs font-semibold uppercase tracking-wide text-muted">
            Qualitative only — no resource model
          </p>
          <h3 className="mt-1 font-sans text-lg font-semibold text-ink">
            {decision?.action_label ?? item.action_label}
          </h3>
          <p className="mt-0.5 text-xs text-muted">{cat.plain}</p>
        </div>
        {decision ? (
          <OutcomeBadge outcome={decision.outcome} priority={decision.priority} />
        ) : null}
      </header>

      <p className="mt-4 flex items-start gap-2 rounded bg-surface-sunken/60 px-3 py-2 text-sm text-body">
        <Info size={15} aria-hidden className="mt-0.5 shrink-0 text-muted" />
        {item.reason}
      </p>

      {decision?.action_basis ? (
        <p className="mt-3 text-sm text-body">{decision.action_basis}</p>
      ) : null}
    </article>
  );
}
