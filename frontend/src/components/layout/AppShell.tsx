import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { useMaybeRunContext } from '@/context/RunContext';
import { FunnelSpine } from './FunnelSpine';
import { BottomNav } from './BottomNav';
import { TopBar } from './TopBar';
import { REFERENCE_LINKS } from './navModel';

/**
 * Frame: fixed left funnel spine (>= lg), global TopBar, centered content,
 * bottom funnel nav (< lg). The spine is full-width at xl, icon-only at lg.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const run = useMaybeRunContext();
  const runId = run?.runId ?? null;

  return (
    <div className="min-h-screen app-grain">
      {/* Left spine */}
      <aside className="fixed inset-y-0 left-0 z-20 hidden border-r border-hairline bg-surface lg:flex lg:w-16 lg:flex-col xl:w-64">
        <div className="flex h-14 items-center border-b border-hairline px-4">
          <Link to="/" className="font-display text-base font-semibold text-ink xl:text-lg">
            <span className="xl:hidden" aria-hidden>
              K
            </span>
            <span className="hidden xl:inline">KAVACH</span>
          </Link>
        </div>
        <div className="flex-1 overflow-y-auto">
          <div className="hidden xl:block">
            <FunnelSpine collapsed={false} />
          </div>
          <div className="xl:hidden">
            <FunnelSpine collapsed />
          </div>
        </div>
        <nav
          aria-label="Reference"
          className="border-t border-hairline p-2 hidden xl:block"
        >
          <p className="mb-1 px-2 font-sans text-[11px] font-semibold uppercase tracking-wide text-muted">
            Reference
          </p>
          <ul className="space-y-0.5">
            {REFERENCE_LINKS.map((l) => (
              <li key={l.key}>
                <Link
                  to={l.to(runId)}
                  className="flex items-center gap-2.5 rounded px-2 py-1.5 text-sm text-muted hover:bg-surface-sunken hover:text-ink"
                >
                  <l.icon size={15} aria-hidden />
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </aside>

      <div className="lg:pl-16 xl:pl-64">
        <TopBar />
        <main className="mx-auto max-w-content px-4 pb-24 pt-8 lg:pb-12">{children}</main>
      </div>

      <BottomNav />
    </div>
  );
}
