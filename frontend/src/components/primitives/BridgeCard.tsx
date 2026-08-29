import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import type { ReactNode } from 'react';

/**
 * The "what this means / what's next" card that ends every funnel screen and
 * moves the reader one step down the funnel.
 */
export function BridgeCard({
  meaning,
  to,
  cta,
}: {
  meaning: ReactNode;
  to: string;
  cta: string;
}) {
  return (
    <Link
      to={to}
      className="group mt-8 flex items-center justify-between gap-4 rounded-lg border border-brand-700/30 bg-brand-tint/50 px-5 py-4 transition-colors hover:bg-brand-tint"
    >
      <p className="text-sm text-body">{meaning}</p>
      <span className="inline-flex shrink-0 items-center gap-1.5 font-sans text-sm font-medium text-brand-700">
        {cta}
        <ArrowRight size={16} aria-hidden className="transition-transform group-hover:translate-x-0.5" />
      </span>
    </Link>
  );
}
