import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/cn';

/**
 * A funnel stage as a large, memorable tile. The whole card is the link (via a
 * stretched overlay anchor) so the `badge` slot can still contain its own
 * interactive tooltip without nesting a button inside an <a>.
 */
export function StageTile({
  index,
  label,
  to,
  headline,
  headlineNote,
  caption,
  badge,
  loading,
  accent = 'brand',
}: {
  index: number;
  label: string;
  to: string;
  headline: ReactNode;
  headlineNote?: ReactNode;
  caption: ReactNode;
  badge?: ReactNode;
  loading?: boolean;
  accent?: 'brand' | 'modeled';
}) {
  return (
    <div className="group relative flex flex-col rounded-lg border border-hairline bg-surface p-5 shadow-card transition-all focus-within:shadow-lift hover:-translate-y-0.5 hover:shadow-lift">
      <div className="mb-3 flex items-center justify-between">
        <span
          className={cn(
            'flex h-8 w-8 items-center justify-center rounded-full border font-sans text-sm font-medium',
            accent === 'modeled'
              ? 'border-modeled text-modeled'
              : 'border-brand-700 bg-brand-700 text-white',
          )}
        >
          {index}
        </span>
        {badge ? <span className="relative z-10">{badge}</span> : null}
      </div>

      <p className="font-sans text-sm font-medium text-muted">{label}</p>
      <p
        className={cn(
          'mt-1 font-display text-3xl font-semibold leading-none sm:text-4xl',
          accent === 'modeled' ? 'text-modeled' : 'text-ink',
        )}
      >
        {loading ? <span className="text-muted">…</span> : headline}
      </p>
      {headlineNote ? <p className="mt-1 text-xs text-muted">{headlineNote}</p> : null}
      <p className="mt-3 flex-1 text-sm text-body">{caption}</p>

      <span className="mt-4 inline-flex items-center gap-1 font-sans text-sm font-medium text-brand-700">
        Open
        <ArrowRight size={15} aria-hidden className="transition-transform group-hover:translate-x-0.5" />
      </span>

      {/* Stretched link overlay — sits under the badge's z-10 layer. */}
      <Link to={to} className="absolute inset-0 rounded-lg" aria-label={`Open ${label}`}>
        <span className="sr-only">Open {label}</span>
      </Link>
    </div>
  );
}
