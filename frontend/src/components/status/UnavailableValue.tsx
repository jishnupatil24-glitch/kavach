import type { ReactNode } from 'react';
import { cn } from '@/lib/cn';

/**
 * The three distinct "no number" states. NEVER rendered as 0, blank, or green.
 *
 *   unavailable    -> backend withheld the value (null / cost UNAVAILABLE)
 *   unknown        -> plant_population.source === "UNKNOWN"
 *   not-evaluated  -> feasibility[].status === "NOT_EVALUATED"
 */
type Kind = 'unavailable' | 'unknown' | 'not-evaluated';

const COPY: Record<Kind, string> = {
  unavailable: 'Unavailable',
  unknown: 'Unknown',
  'not-evaluated': 'Not evaluated',
};

export function UnavailableValue({
  kind,
  why,
  action,
  inline = false,
  className,
}: {
  kind: Kind;
  /** Short reason, e.g. the matching limitations[] entry. */
  why?: ReactNode;
  /** Optional CTA, e.g. link to Farm Setup for `unknown`. */
  action?: ReactNode;
  inline?: boolean;
  className?: string;
}) {
  if (inline) {
    return (
      <span
        className={cn('font-sans text-sm italic text-muted', className)}
        title={typeof why === 'string' ? why : undefined}
      >
        {COPY[kind]}
      </span>
    );
  }
  return (
    <div
      className={cn(
        'rounded border border-dashed border-hairline bg-surface-sunken/60 px-3 py-2',
        className,
      )}
    >
      <p className="font-sans text-sm font-medium italic text-muted">{COPY[kind]}</p>
      {why ? <p className="mt-1 text-xs text-muted">{why}</p> : null}
      {action ? <div className="mt-2">{action}</div> : null}
    </div>
  );
}
