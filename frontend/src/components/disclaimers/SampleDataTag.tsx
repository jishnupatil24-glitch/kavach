import { Database } from 'lucide-react';
import { OPTIMIZATION_IS_MOCKED } from '@/api/endpoints/optimization';

/**
 * Rendered while the optimization data comes from the local fixture adapter
 * (VITE_MOCK_OPTIMIZATION !== "false") rather than a real backend route.
 * Disappears automatically once the flag is flipped.
 */
export function SampleDataTag({ className }: { className?: string }) {
  if (!OPTIMIZATION_IS_MOCKED) return null;
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-pill border border-dashed border-muted px-2.5 py-1 font-sans text-xs font-medium text-muted ${className ?? ''}`}
      title="Phase 6 has no backend route yet — this view is served by a contract-shaped fixture."
    >
      <Database size={12} aria-hidden />
      Sample data — backend not yet connected
    </span>
  );
}
