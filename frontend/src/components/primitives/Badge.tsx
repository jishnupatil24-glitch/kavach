import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '@/lib/cn';

interface Props extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  /** visual weight */
  tone?: 'solid' | 'outline' | 'dashed' | 'muted';
  className?: string;
}

const tones: Record<NonNullable<Props['tone']>, string> = {
  solid: 'text-white',
  outline: 'border bg-transparent',
  dashed: 'border border-dashed bg-transparent',
  muted: 'bg-surface-sunken text-muted border border-hairline',
};

/**
 * Neutral pill base. Status meaning always comes from the dedicated status
 * components (EvidenceIndicator / SeverityBadge / OutcomeBadge / ...), never
 * from a bare Badge with an arbitrary colour.
 */
export function Badge({ children, tone = 'muted', className, style, ...rest }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-pill px-2 py-0.5 text-xs font-sans font-medium',
        tones[tone],
        className,
      )}
      style={style}
      {...rest}
    >
      {children}
    </span>
  );
}
