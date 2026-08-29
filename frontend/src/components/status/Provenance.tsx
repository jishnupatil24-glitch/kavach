import type { ReactNode } from 'react';
import { PROVENANCE } from '@/lib/plain-language';
import { cn } from '@/lib/cn';
import { InfoTooltip } from '../primitives/InfoTooltip';

/**
 * Provenance dot — attached to EVERY measured number.
 *   SOURCED         ● filled   (cited external fact, highest confidence)
 *   PROJECT_DEFINED ◐ half     (KAVACH assumption — not validated; amber)
 *   MODELED         ○ hollow   (deterministic calculation)
 */
export function ProvenanceDot({ provenance }: { provenance: string }) {
  const term = PROVENANCE[provenance] ?? PROVENANCE.MODELED;
  const key = term.technical;

  return (
    <InfoTooltip
      label={`Provenance: ${term.plain}`}
      content={
        <span>
          <strong className="font-sans">{term.plain}</strong>{' '}
          <span className="text-xs text-muted">({key})</span>
          <br />
          {term.description}
        </span>
      }
    >
      <button
        type="button"
        aria-label={`Provenance: ${term.plain} (${key})`}
        className="inline-flex h-4 w-4 items-center justify-center align-middle"
      >
        <span
          aria-hidden
          className={cn(
            'inline-block h-2.5 w-2.5 rounded-full border',
            key === 'SOURCED' && 'border-brand-900 bg-brand-900',
            key === 'PROJECT_DEFINED' && 'border-gold bg-gradient-to-r from-gold to-transparent',
            key !== 'SOURCED' && key !== 'PROJECT_DEFINED' && 'border-muted bg-transparent',
          )}
        />
      </button>
    </InfoTooltip>
  );
}

/** Number + its provenance dot, the standard pairing across the app. */
export function ValueWithProvenance({
  children,
  provenance,
  className,
}: {
  children: ReactNode;
  provenance: string | null | undefined;
  className?: string;
}) {
  return (
    <span className={cn('inline-flex items-baseline gap-1.5', className)}>
      <span className="font-mono">{children}</span>
      {provenance ? <ProvenanceDot provenance={provenance} /> : null}
    </span>
  );
}

export function ProvenanceLegend() {
  return (
    <ul className="space-y-2 text-sm">
      {(['SOURCED', 'PROJECT_DEFINED', 'MODELED'] as const).map((k) => (
        <li key={k} className="flex items-start gap-3">
          <span className="mt-1">
            <ProvenanceDot provenance={k} />
          </span>
          <span>
            <span className="font-sans font-medium text-ink">{PROVENANCE[k].plain}</span>{' '}
            <span className="text-xs text-muted">({k})</span>
            <br />
            <span className="text-muted">{PROVENANCE[k].description}</span>
          </span>
        </li>
      ))}
    </ul>
  );
}
