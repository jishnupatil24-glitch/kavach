import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/cn';
import { useMaybeRunContext } from '@/context/RunContext';
import { useFunnelSummary } from '@/features/overview/useFunnelSummary';
import { FUNNEL } from './navModel';

/**
 * The funnel spine — vertical, numbered, connected. This is the primary nav on
 * desktop and the visual signature of the product. Count badges come from the
 * same cached queries the pages use.
 */
export function FunnelSpine({ collapsed }: { collapsed: boolean }) {
  const run = useMaybeRunContext();
  const location = useLocation();
  const runId = run?.runId ?? null;
  const effectiveDay = run?.day ?? null;
  const summary = useFunnelSummary(runId, effectiveDay);

  const search = run?.rawDay != null ? `?day=${run.rawDay}` : '';

  return (
    <nav
      aria-label="Decision funnel"
      className={cn(
        'flex h-full flex-col gap-1 px-2 py-4',
        collapsed ? 'items-center' : 'items-stretch',
      )}
    >
      {!collapsed && (
        <p className="mb-2 px-2 font-sans text-[11px] font-semibold uppercase tracking-wide text-muted">
          Decision funnel
        </p>
      )}
      <ol className="relative flex flex-col gap-1">
        <span
          aria-hidden
          className={cn(
            'absolute left-[19px] top-4 bottom-4 w-px bg-hairline',
            collapsed && 'left-1/2 -translate-x-1/2',
          )}
        />
        {FUNNEL.map((node) => {
          const count = summary.counts[node.key];
          const disabled = runId == null;
          const to = disabled ? '#' : `${node.to(runId)}${search}`;
          const isActive =
            node.key === 'overview'
              ? /\/runs\/\d+$/.test(location.pathname)
              : location.pathname.includes(`/${node.match}`);

          const inner = (
            <>
              <span
                className={cn(
                  'z-10 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border font-sans text-sm',
                  isActive
                    ? 'border-brand-700 bg-brand-700 text-white'
                    : 'border-hairline bg-surface text-muted',
                )}
              >
                {node.marker}
              </span>
              {!collapsed && (
                <span className="flex min-w-0 flex-1 items-center justify-between gap-2">
                  <span
                    className={cn(
                      'truncate font-sans text-sm',
                      isActive ? 'font-medium text-ink' : 'text-body',
                    )}
                  >
                    {node.label}
                  </span>
                  {count != null && count.value != null ? (
                    <span
                      className="shrink-0 rounded-pill bg-surface-sunken px-1.5 text-xs text-muted"
                      title={count.hint}
                    >
                      {count.value}
                    </span>
                  ) : null}
                </span>
              )}
            </>
          );

          return (
            <li key={node.key}>
              {disabled ? (
                <span
                  className="flex items-center gap-3 rounded px-2 py-1.5 opacity-50"
                  title="Pick a run first"
                  aria-disabled
                >
                  {inner}
                </span>
              ) : (
                <NavLink
                  to={to}
                  className={cn(
                    'flex items-center gap-3 rounded px-2 py-1.5 transition-colors hover:bg-surface-sunken',
                    collapsed && 'justify-center',
                  )}
                  aria-current={isActive ? 'page' : undefined}
                  title={collapsed ? node.label : undefined}
                >
                  {inner}
                </NavLink>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
