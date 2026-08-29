import type { TrendDirection } from '@/api/types';
import { TREND_DIRECTION } from '@/lib/plain-language';
import { formatRate } from '@/lib/format';
import { ArrowDownRight, ArrowUpRight, HelpCircle, Minus } from 'lucide-react';
import { cn } from '@/lib/cn';

const ICON: Record<TrendDirection, typeof Minus> = {
  RISING: ArrowUpRight,
  FALLING: ArrowDownRight,
  STABLE: Minus,
  UNDETERMINED: HelpCircle,
};

export function TrendBadge({
  direction,
  rate,
  rateUnit,
  className,
}: {
  direction: TrendDirection;
  rate?: number | null;
  rateUnit?: string | null;
  className?: string;
}) {
  const term = TREND_DIRECTION[direction] ?? TREND_DIRECTION.UNDETERMINED;
  const Icon = ICON[direction] ?? HelpCircle;
  const r = formatRate(rate ?? null, rateUnit ?? null);
  return (
    <span
      className={cn('inline-flex items-center gap-1 font-sans text-sm text-body', className)}
      title={term.description}
    >
      <Icon size={15} aria-hidden className="text-muted" />
      <span>{term.plain}</span>
      {r ? <span className="font-mono text-xs text-muted">({r})</span> : null}
    </span>
  );
}
