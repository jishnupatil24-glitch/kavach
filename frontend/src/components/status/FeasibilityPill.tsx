import type { FeasibilityStatus } from '@/api/types';
import { FEASIBILITY } from '@/lib/plain-language';
import { Check, Minus, X } from 'lucide-react';
import { cn } from '@/lib/cn';

/**
 * PASS / FAIL / NOT_EVALUATED — three visually distinct pills.
 * NOT_EVALUATED is grey with a dash and must never read as PASS.
 */
export function FeasibilityPill({
  status,
  label,
  className,
}: {
  status: FeasibilityStatus;
  label?: string;
  className?: string;
}) {
  const term = FEASIBILITY[status];
  const map = {
    PASS: { cls: 'bg-feas-pass text-white', Icon: Check },
    FAIL: { cls: 'bg-feas-fail text-white', Icon: X },
    NOT_EVALUATED: { cls: 'border border-dashed border-muted text-muted', Icon: Minus },
  }[status];
  const { Icon } = map;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-pill px-2.5 py-1 font-sans text-xs font-medium',
        map.cls,
        className,
      )}
      title={term.description}
    >
      <Icon size={13} aria-hidden />
      {label ? `${humanLabel(label)}: ` : ''}
      {term.plain}
    </span>
  );
}

function humanLabel(l: string): string {
  const map: Record<string, string> = {
    available_water: 'Water supply',
    pump_capacity: 'Pump capacity',
  };
  return map[l] ?? l.replace(/[_-]+/g, ' ');
}
