import { HelpCircle } from 'lucide-react';
import type { Problem } from '@/api/types';
import { CATEGORY } from '@/lib/plain-language';
import { formatNumber } from '@/lib/format';
import { variableByField } from '@/lib/variables';
import { EvidenceIndicator } from '@/components/status/EvidenceIndicator';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { AbnormalDurationTag } from '@/components/status/AbnormalDurationTag';
import { DeviationChip } from '@/components/status/DeviationChip';
import { Button } from '@/components/primitives/Button';

export function ProblemCard({
  problem,
  onWhy,
}: {
  problem: Problem;
  onWhy: () => void;
}) {
  const cat = CATEGORY[problem.category] ?? { plain: problem.label, technical: problem.category };
  const variable = variableByField(problem.field);
  const unit = variable?.unit ?? '';

  return (
    <article className="card flex flex-col p-5">
      <header>
        <h3 className="font-sans text-base font-semibold text-ink">{cat.plain}</h3>
        <p className="mt-0.5 text-xs text-muted">
          {problem.label} · <code className="font-mono">{problem.category}</code>
        </p>
      </header>

      {/* Evidence and severity are two named, visually distinct axes. */}
      <div className="mt-4 flex flex-wrap gap-x-6 gap-y-3 rounded-lg border border-hairline bg-surface-sunken/40 p-3">
        <div>
          <p className="mb-1 font-sans text-[11px] font-semibold uppercase tracking-wide text-muted">
            Evidence
          </p>
          <EvidenceIndicator status={problem.status} />
        </div>
        <div className="border-l border-hairline pl-6">
          <p className="mb-1 font-sans text-[11px] font-semibold uppercase tracking-wide text-muted">
            Severity
          </p>
          <SeverityBadge severity={problem.severity} />
        </div>
      </div>

      <dl className="mt-4 space-y-1.5 text-sm">
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted">Current</dt>
          <dd className="font-mono text-ink">
            {formatNumber(problem.current_value, variable?.precision ?? 1) ?? '—'}
            {unit ? ` ${unit}` : ''}
          </dd>
        </div>
        <div className="flex items-center justify-between gap-2">
          <dt className="text-muted">Vs reference</dt>
          <dd>
            <DeviationChip value={problem.icar_deviation} unitSuffix={unit ? ` ${unit}` : ''} />
          </dd>
        </div>
      </dl>

      <div className="mt-3">
        <AbnormalDurationTag
          days={problem.abnormal_state_duration.days}
          tier={problem.abnormal_state_duration.tier}
        />
      </div>

      <div className="mt-auto pt-4">
        <Button size="sm" variant="secondary" onClick={onWhy} className="w-full">
          <HelpCircle size={14} aria-hidden />
          Why did KAVACH say this?
        </Button>
      </div>
    </article>
  );
}
