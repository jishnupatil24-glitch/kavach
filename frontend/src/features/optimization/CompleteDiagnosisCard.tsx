import type { ReactNode } from 'react';
import { ArrowRight } from 'lucide-react';
import type { DecisionRecord, WaterOptimization } from '@/api/types';
import { CATEGORY } from '@/lib/plain-language';
import { formatNumber, isMissing } from '@/lib/format';
import { classifyWaterImpact } from '@/lib/waterImpact';
import { estimateRecoveryWindow } from '@/lib/recoveryEstimate';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { EvidenceIndicator } from '@/components/status/EvidenceIndicator';
import { UnavailableValue } from '@/components/status/UnavailableValue';

/**
 * Phase 5 + Phase 6 fused into one glance: problem -> evidence/severity ->
 * recommended action -> quantities -> water impact -> expected response ->
 * review -> next decision. Every field here already exists on `decision`/
 * `opt` (both fetched from the real backend) — nothing here is computed,
 * except the recovery window, which is explicitly labelled as a frontend
 * prototype estimate (see lib/recoveryEstimate.ts).
 */
export function CompleteDiagnosisCard({
  decision,
  opt,
}: {
  decision: DecisionRecord | undefined;
  opt: WaterOptimization;
}) {
  const cat = CATEGORY[opt.category] ?? { plain: opt.action_label };
  const havePopulation = opt.plant_population.source !== 'UNKNOWN';
  const impact = classifyWaterImpact(
    havePopulation ? opt.water_saved_vs_typical_l_per_day : null,
    havePopulation ? opt.water_saved_vs_typical_percentage : null,
  );
  const recovery = estimateRecoveryWindow({
    severity: opt.severity,
    reviewCycleDays: opt.review_cycle_days,
    expectedDirection: opt.expected_direction,
  });

  const actionVerb = opt.direction === 'increase' ? 'Increase irrigation' : 'Reduce irrigation';

  return (
    <div className="rounded-lg border border-hairline bg-surface-sunken/40 p-5">
      <p className="font-sans text-xs font-semibold uppercase tracking-wide text-muted">
        Complete diagnosis
      </p>

      <div className="mt-3 grid gap-4 sm:grid-cols-2">
        <div>
          <p className="text-xs text-muted">Problem</p>
          <p className="font-sans text-base font-semibold text-ink">{cat.plain}</p>
        </div>
        <div>
          <p className="text-xs text-muted">Severity</p>
          <SeverityBadge severity={opt.severity} />
        </div>
        {decision ? (
          <div>
            <p className="text-xs text-muted">Evidence</p>
            <EvidenceIndicator status={decision.status} />
          </div>
        ) : null}
        {decision?.abnormal_duration_days != null ? (
          <div>
            <p className="text-xs text-muted">Abnormal duration</p>
            <p className="font-mono text-sm text-body">{decision.abnormal_duration_days} days</p>
          </div>
        ) : null}
      </div>

      <div className="mt-4 border-t border-hairline pt-4">
        <p className="text-xs text-muted">Recommended action</p>
        <p className="font-display text-xl font-semibold text-ink">{actionVerb}</p>
      </div>

      <div className="mt-4 grid gap-3 border-t border-hairline pt-4 sm:grid-cols-3">
        <div>
          <p className="text-xs text-muted">Typical application</p>
          <p className="font-mono text-sm text-body">
            {isMissing(opt.typical_l_per_plant_day)
              ? '—'
              : `${formatNumber(opt.typical_l_per_plant_day, 2)} L/plant/day`}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">Theoretical crop requirement</p>
          <p className="font-mono text-sm text-body">
            {isMissing(opt.baseline_l_per_plant_day)
              ? '—'
              : `${formatNumber(opt.baseline_l_per_plant_day, 2)} L/plant/day`}
          </p>
        </div>
        <div>
          <p className="text-xs text-muted">KAVACH recommendation</p>
          <p className="font-mono text-sm font-semibold text-modeled">
            {isMissing(opt.optimized_l_per_plant_day)
              ? '—'
              : `${formatNumber(opt.optimized_l_per_plant_day, 2)} L/plant/day`}
          </p>
        </div>
      </div>

      <div className="mt-4 border-t border-hairline pt-4">
        {impact.kind === 'unavailable' ? (
          <UnavailableValue kind="unavailable" why="Water impact vs typical application is unavailable for this day." />
        ) : impact.kind === 'equal' ? (
          <p className="text-sm text-body">No difference vs typical application.</p>
        ) : (
          <p className="font-sans text-sm text-body">
            <span className={impact.kind === 'saved' ? 'font-semibold text-feas-pass' : 'font-semibold text-sev-high'}>
              {formatNumber(impact.magnitudePerDay, 0)} L/day{' '}
              {impact.kind === 'saved' ? 'saved' : 'additional water required'}
            </span>{' '}
            vs typical application
            {impact.magnitudePct != null ? ` (${formatNumber(impact.magnitudePct, 1)}%)` : ''}.
          </p>
        )}
      </div>

      <div className="mt-4 border-t border-hairline pt-4">
        <p className="text-xs text-muted">Recovery estimate</p>
        {recovery ? (
          <>
            <p className="font-sans text-sm font-medium text-ink">
              {recovery.lowDays}–{recovery.highDays} days · confidence {recovery.confidence}
            </p>
            <p className="mt-1 text-xs text-muted">
              {recovery.basis} MODELED PROTOTYPE — NOT SCIENTIFICALLY VALIDATED.
            </p>
          </>
        ) : (
          <UnavailableValue
            kind="unavailable"
            why="KAVACH currently models expected direction but does not contain a validated recovery-time model."
          />
        )}
      </div>

      <div className="mt-5 border-t border-hairline pt-4">
        <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">What happens next</p>
        <ol className="flex flex-wrap items-center gap-x-2 gap-y-3 font-sans text-sm text-body">
          <Step>{actionVerb}</Step>
          <Arrow />
          <Step>
            {impact.kind === 'saved' || impact.kind === 'additional'
              ? `${formatNumber(impact.magnitudePerDay, 0)} L/day ${impact.kind === 'saved' ? 'saved' : 'more needed'}`
              : 'Water impact unavailable'}
          </Step>
          <Arrow />
          <Step>Moisture expected: {opt.expected_direction}</Step>
          <Arrow />
          <Step>Reassess in {opt.review_cycle_days ?? '—'} days</Step>
          <Arrow />
          <Step>Re-run Phase 5/6 on the latest measured state</Step>
        </ol>
      </div>
    </div>
  );
}

function Step({ children }: { children: ReactNode }) {
  return (
    <li className="rounded border border-hairline bg-surface px-3 py-1.5">{children}</li>
  );
}

function Arrow() {
  return <ArrowRight size={14} aria-hidden className="shrink-0 text-muted" />;
}
