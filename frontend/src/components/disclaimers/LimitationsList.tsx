import { AlertTriangle } from 'lucide-react';
import { cn } from '@/lib/cn';

/**
 * Renders a backend `limitations[]` array verbatim. Never summarised, never
 * dropped — the backend treats hiding these as a correctness bug.
 */
export function LimitationsList({
  items,
  title = 'Limitations & assumptions',
  className,
}: {
  items: string[];
  title?: string;
  className?: string;
}) {
  if (!items?.length) return null;
  return (
    <div
      className={cn('rounded-lg border border-hairline bg-surface-sunken/60 p-4', className)}
    >
      <p className="mb-2 flex items-center gap-2 font-sans text-sm font-semibold text-ink">
        <AlertTriangle size={15} aria-hidden className="text-gold" />
        {title}
      </p>
      <ul className="list-disc space-y-1.5 pl-5 text-sm text-body">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}
