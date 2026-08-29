import type { Severity } from '@/api/types';
import { SEVERITY } from '@/lib/plain-language';
import { cn } from '@/lib/cn';
import { InfoTooltip } from '../primitives/InfoTooltip';

/**
 * Severity — the "how bad" axis. Hue ramp, filled band. Independent of
 * evidence: a `no_evidence` problem can still carry a non-trivial severity,
 * and the UI must not conflate the two.
 */
const HUE: Record<Severity, string> = {
  insufficient_data: 'rgb(var(--muted))',
  LOW: 'rgb(var(--sev-low))',
  MODERATE: 'rgb(var(--sev-moderate))',
  HIGH: 'rgb(var(--sev-high))',
  CRITICAL: 'rgb(var(--sev-critical))',
};

export function SeverityBadge({
  severity,
  className,
}: {
  severity: Severity;
  className?: string;
}) {
  const term = SEVERITY[severity];
  const hue = HUE[severity];
  const hollow = severity === 'insufficient_data';
  const critical = severity === 'CRITICAL';

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded px-2 py-0.5 font-sans text-sm font-medium',
          critical && 'motion-safe:animate-pulse-once',
        )}
        style={
          hollow
            ? { border: `1px solid ${hue}`, color: hue }
            : { background: hue, color: '#fff' }
        }
      >
        {term.plain}
      </span>
      <InfoTooltip
        label={`Severity: ${term.plain}`}
        content={
          <span>
            <strong className="font-sans">Severity — {term.plain}</strong>
            <br />
            {term.description}
            <br />
            <span className="text-xs text-muted">
              A deterministic observational score, not itself an agronomic diagnosis. Independent of
              evidence.
            </span>
          </span>
        }
      />
      <span className="sr-only">Severity: {term.plain}</span>
    </span>
  );
}
