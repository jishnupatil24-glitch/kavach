import { FlaskConical } from 'lucide-react';

/**
 * Non-dismissible. Shown at the top of every Phase 6 (Optimized Plan) view.
 * The copy is taken verbatim from every optimization response's limitations[].
 */
export function PrototypeBanner() {
  return (
    <div
      role="note"
      className="prototype-hatch mb-6 flex items-start gap-3 rounded-lg border border-gold/50 px-4 py-3"
    >
      <span className="mt-0.5 rounded bg-surface/80 p-1 text-gold">
        <FlaskConical size={16} aria-hidden />
      </span>
      <div className="rounded bg-surface/80 px-2 py-1 text-sm">
        <p className="font-sans font-semibold text-ink">Prototype optimization model.</p>
        <p className="text-body">
          Numbers here are illustrative, not a validated agronomic prescription. Every value is a
          KAVACH assumption or a calculation from one.
        </p>
      </div>
    </div>
  );
}
