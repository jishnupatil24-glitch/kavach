import { Database } from 'lucide-react';
import { OPTIMIZATION_IS_MOCKED } from '@/api/endpoints/optimization';

/**
 * Rendered while the optimization data comes from the local fixture adapter
 * (VITE_MOCK_OPTIMIZATION="true") instead of the real, implemented backend
 * route. Disappears automatically once the flag is unset/false.
 */
export function SampleDataTag({ className }: { className?: string }) {
  if (!OPTIMIZATION_IS_MOCKED) return null;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-pill border border-dashed border-muted px-2.5 py-1 font-sans text-xs font-medium text-muted ${className ?? ''}`}
      title="VITE_MOCK_OPTIMIZATION is forced on — this view is served by a contract-shaped fixture instead of the live backend."
    >
      <Database size={12} aria-hidden />
      Sample data — backend not yet connected
    </span>
  );
}
