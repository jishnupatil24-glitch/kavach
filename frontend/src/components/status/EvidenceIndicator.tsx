import type { EvidenceStatus } from '@/api/types';
import { EVIDENCE_STATUS } from '@/lib/plain-language';
import { cn } from '@/lib/cn';
import { InfoTooltip } from '../primitives/InfoTooltip';

/**
 * Evidence status — the "how sure are we" axis.
 * Encoded MONOCHROME as filled signal bars (0..3) + a chip. Never hue: that is
 * reserved for severity, so the two axes can never be visually confused.
 */
const BARS: Record<EvidenceStatus, number> = {
  insufficient_data: 0,
  no_evidence: 0,
  weak_evidence: 2,
  corroborated_evidence: 3,
};

export function EvidenceIndicator({
  status,
  showLabel = true,
  className,
}: {
  status: EvidenceStatus;
  showLabel?: boolean;
  className?: string;
}) {
  const term = EVIDENCE_STATUS[status];
  const bars = BARS[status];
  const dashed = status === 'insufficient_data';

  return (
    <span className={cn('inline-flex items-center gap-2', className)}>
      <span
        className={cn(
          'inline-flex items-end gap-[2px] rounded-sm border px-1.5 py-1',
          dashed ? 'border-dashed' : 'border-solid',
        )}
        style={{ borderColor: 'var(--evidence-track)' }}
        aria-hidden
      >
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-[3px] rounded-[1px]"
            style={{
              height: `${6 + i * 3}px`,
              background: i < bars ? 'var(--evidence-ink)' : 'var(--evidence-track)',
            }}
          />
        ))}
      </span>
      {showLabel ? (
        <span className="font-sans text-sm text-ink">{term.plain}</span>
      ) : null}
      <InfoTooltip
        label={`Evidence: ${term.plain}`}
        content={
          <span>
            <strong className="font-sans">Evidence — {term.plain}</strong>
            <br />
            <span className="text-xs text-muted">({term.technical})</span>
            <br />
            {term.description}
          </span>
        }
      />
      <span className="sr-only">
        Evidence status: {term.plain} ({term.technical})
      </span>
    </span>
  );
}
