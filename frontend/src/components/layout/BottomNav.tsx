import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/cn';
import { useMaybeRunContext } from '@/context/RunContext';
import { FUNNEL } from './navModel';

/** 5-item bottom nav for < lg screens (the funnel, nothing else). */
export function BottomNav() {
  const run = useMaybeRunContext();
  const location = useLocation();
  const runId = run?.runId ?? null;
  const search = run?.rawDay != null ? `?day=${run.rawDay}` : '';

  if (runId == null) return null;

  return (
    <nav
      aria-label="Decision funnel"
      className="fixed inset-x-0 bottom-0 z-30 flex border-t border-hairline bg-surface lg:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {FUNNEL.map((node) => {
        const Icon = node.icon;
        const isActive =
          node.key === 'overview'
            ? /\/runs\/\d+$/.test(location.pathname)
            : location.pathname.includes(`/${node.match}`);
        return (
          <NavLink
            key={node.key}
            to={`${node.to(runId)}${search}`}
            aria-current={isActive ? 'page' : undefined}
            className={cn(
              'flex min-h-[56px] flex-1 flex-col items-center justify-center gap-0.5 px-1 py-1.5 text-[11px]',
              isActive ? 'text-brand-700' : 'text-muted',
            )}
          >
            <Icon size={18} aria-hidden />
            <span className="truncate">{node.label.replace('Optimized ', '')}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
