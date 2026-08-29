import { Link, useLocation } from 'react-router-dom';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/cn';
import { useRunContext } from '@/context/RunContext';
import { FUNNEL } from './navModel';

/** Compact horizontal funnel shown in the page header on small screens. */
export function FunnelEcho() {
  const { runId, rawDay } = useRunContext();
  const location = useLocation();
  const search = rawDay != null ? `?day=${rawDay}` : '';

  const activeIndex = FUNNEL.findIndex((n) =>
    n.key === 'overview'
      ? /\/runs\/\d+$/.test(location.pathname)
      : location.pathname.includes(`/${n.match}`),
  );
  const idx = activeIndex === -1 ? 0 : activeIndex;
  const prev = FUNNEL[idx - 1];
  const next = FUNNEL[idx + 1];

  return (
    <div className="flex items-center justify-between gap-2 lg:hidden">
      <div>
        {prev ? (
          <Link
            to={`${prev.to(runId)}${search}`}
            className="inline-flex items-center gap-1 text-sm text-brand-700"
          >
            <ChevronLeft size={16} aria-hidden />
            {prev.label}
          </Link>
        ) : (
          <span />
        )}
      </div>
      <ol className="flex items-center gap-1.5" aria-label="Funnel progress">
        {FUNNEL.map((n, i) => (
          <li
            key={n.key}
            aria-current={i === idx ? 'step' : undefined}
            className={cn(
              'h-1.5 rounded-pill transition-all',
              i === idx ? 'w-5 bg-brand-700' : 'w-1.5 bg-hairline',
            )}
          />
        ))}
      </ol>
      <div className="text-right">
        {next ? (
          <Link
            to={`${next.to(runId)}${search}`}
            className="inline-flex items-center gap-1 text-sm text-brand-700"
          >
            {next.label}
            <ChevronRight size={16} aria-hidden />
          </Link>
        ) : (
          <span />
        )}
      </div>
    </div>
  );
}
