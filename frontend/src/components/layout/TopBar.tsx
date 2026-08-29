import { Link } from 'react-router-dom';
import { HelpCircle } from 'lucide-react';
import { useMaybeRunContext } from '@/context/RunContext';
import { RunSwitcher } from './RunSwitcher';
import { DayScrubber } from './DayScrubber';
import { ThemeToggle } from './ThemeToggle';

/**
 * Global context bar:
 *   KAVACH · [ Run … ▾ ] · [ ‹ Day n / N › ] · [ ? Legend ] · [ theme ]
 * Run switcher + day scrubber appear only when a run is in context.
 */
export function TopBar() {
  const run = useMaybeRunContext();

  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-surface/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-content items-center gap-3 px-4">
        <Link to="/" className="flex items-center gap-2 font-display text-lg font-semibold text-ink">
          <span
            aria-hidden
            className="inline-block h-2.5 w-2.5 rounded-sm bg-brand-700"
            style={{ transform: 'rotate(45deg)' }}
          />
          KAVACH
        </Link>

        {run ? (
          <>
            <span aria-hidden className="text-hairline">
              ·
            </span>
            <RunSwitcher />
            <div className="hidden sm:block">
              <DayScrubber />
            </div>
          </>
        ) : null}

        <div className="ml-auto flex items-center gap-2">
          <Link
            to="/about"
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-hairline px-3 text-sm text-muted hover:text-ink"
          >
            <HelpCircle size={15} aria-hidden />
            <span className="hidden sm:inline">Legend</span>
          </Link>
          <ThemeToggle />
        </div>
      </div>
      {run ? (
        <div className="mx-auto max-w-content px-4 pb-2 sm:hidden">
          <DayScrubber className="w-full justify-between" />
        </div>
      ) : null}
    </header>
  );
}
