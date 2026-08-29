import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, RotateCw } from 'lucide-react';
import { ApiError } from '@/api/client';
import { cn } from '@/lib/cn';
import { Button } from './Button';

/* ---------------- Empty (calm, never an error) ---------------- */

export function EmptyState({
  title,
  hint,
  icon,
  action,
  className,
}: {
  title: string;
  hint?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border border-dashed border-hairline bg-surface-sunken/50 px-6 py-12 text-center',
        className,
      )}
    >
      <div className="mb-3 text-muted">{icon ?? <Inbox size={24} aria-hidden />}</div>
      <p className="font-sans text-base text-ink">{title}</p>
      {hint ? <p className="mt-1 max-w-md text-sm text-muted">{hint}</p> : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}

/* ---------------- Error (role=alert, shows API detail) ---------------- */

export function ErrorState({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const detail =
    error instanceof ApiError
      ? error.detail
      : error instanceof Error
        ? error.message
        : 'Something went wrong.';
  const status = error instanceof ApiError ? error.httpStatus : undefined;

  return (
    <div
      role="alert"
      className={cn(
        'rounded-lg border border-feas-fail/40 bg-feas-fail/5 px-5 py-4 text-sm',
        className,
      )}
    >
      <div className="flex items-start gap-3">
        <AlertTriangle size={18} className="mt-0.5 shrink-0 text-feas-fail" aria-hidden />
        <div className="flex-1">
          <p className="font-sans font-medium text-ink">
            {status ? `Request failed (HTTP ${status})` : 'Request failed'}
          </p>
          <p className="mt-1 text-body">{detail}</p>
          {onRetry ? (
            <Button size="sm" variant="secondary" className="mt-3" onClick={onRetry}>
              <RotateCw size={14} aria-hidden /> Try again
            </Button>
          ) : null}
        </div>
      </div>
    </div>
  );
}

/* ---------------- Loading (layout-reserving skeletons) ---------------- */

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn('animate-pulse rounded bg-surface-sunken', className)}
      aria-hidden
    />
  );
}

export function SkeletonCard({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn('card p-6', className)} aria-busy="true" aria-live="polite">
      <Skeleton className="h-4 w-1/3" />
      <div className="mt-4 space-y-2">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton key={i} className={cn('h-3', i === lines - 1 ? 'w-2/3' : 'w-full')} />
        ))}
      </div>
      <span className="sr-only">Loading…</span>
    </div>
  );
}

export function SkeletonGrid({ count = 6 }: { count?: number }) {
  return (
    <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} />
      ))}
    </div>
  );
}
