import type { Outcome } from '@/api/types';
import { OUTCOME } from '@/lib/plain-language';
import { cn } from '@/lib/cn';
import { AlertCircle, Eye, MinusCircle, ShieldQuestion, Zap } from 'lucide-react';

const STYLE: Record<Outcome, { className: string; icon: typeof Zap }> = {
  ACTION_RECOMMENDED: { className: 'bg-brand-700 text-white', icon: Zap },
  MONITOR: { className: 'border border-sev-moderate text-sev-moderate', icon: Eye },
  NO_ACTION: { className: 'bg-surface-sunken text-muted border border-hairline', icon: MinusCircle },
  INSUFFICIENT_SUPPORT: {
    className: 'border border-dashed border-muted text-muted',
    icon: ShieldQuestion,
  },
  CONFLICT: { className: 'border border-feas-fail text-feas-fail', icon: AlertCircle },
};

export function OutcomeBadge({
  outcome,
  priority,
  className,
}: {
  outcome: Outcome;
  priority?: number | null;
  className?: string;
}) {
  const term = OUTCOME[outcome];
  const s = STYLE[outcome];
  const Icon = s.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 font-sans text-sm font-medium',
        s.className,
        className,
      )}
      title={`${term.plain} (${term.technical})`}
    >
      <Icon size={14} aria-hidden />
      {term.plain}
      {outcome === 'ACTION_RECOMMENDED' && priority != null ? (
        <span className="ml-0.5 rounded-full bg-white/25 px-1.5 text-xs">#{priority}</span>
      ) : null}
    </span>
  );
}
