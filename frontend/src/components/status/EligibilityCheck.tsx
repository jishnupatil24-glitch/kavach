import type { GateCheck } from '@/api/types';
import { Check, CircleSlash, X } from 'lucide-react';
import { cn } from '@/lib/cn';

/**
 * Tri-state eligibility check:
 *   true  -> Met
 *   false -> Not met  (orange, not red: a failed gate is normal, not an error)
 *   null  -> Can't evaluate  (grey — never coerced to pass or fail)
 */
function state(passed: boolean | null) {
  if (passed === true)
    return { label: 'Met', icon: Check, cls: 'text-feas-pass', iconCls: 'text-feas-pass' };
  if (passed === false)
    return { label: 'Not met', icon: X, cls: 'text-sev-high', iconCls: 'text-sev-high' };
  return {
    label: "Can't evaluate",
    icon: CircleSlash,
    cls: 'text-muted',
    iconCls: 'text-muted',
  };
}

export function EligibilityCheckRow({ check }: { check: GateCheck }) {
  const s = state(check.passed);
  const Icon = s.icon;
  return (
    <li className="flex items-start gap-3 py-2">
      <Icon size={16} className={cn('mt-0.5 shrink-0', s.iconCls)} aria-hidden />
      <div className="min-w-0">
        <p className="font-sans text-sm text-ink">
          {humanCheckName(check.name)} — <span className={s.cls}>{s.label}</span>
        </p>
        <p className="mt-0.5 break-words text-xs text-muted">{check.detail}</p>
      </div>
    </li>
  );
}

export function EligibilityChecklist({ checks }: { checks: GateCheck[] }) {
  if (!checks.length) {
    return <p className="text-sm text-muted">No eligibility checks were recorded.</p>;
  }
  return (
    <ul className="divide-y divide-hairline">
      {checks.map((c) => (
        <EligibilityCheckRow key={c.name} check={c} />
      ))}
    </ul>
  );
}

function humanCheckName(name: string): string {
  const map: Record<string, string> = {
    evidence_status: 'Evidence status',
    severity_floor: 'Severity floor',
    duration_floor: 'Abnormal-duration floor',
  };
  return map[name] ?? name.replace(/[_-]+/g, ' ');
}
