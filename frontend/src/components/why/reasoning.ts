import type { DecisionRecord, Problem } from '@/api/types';
import { CATEGORY, EVIDENCE_STATUS, OUTCOME, TREND_DIRECTION } from '@/lib/plain-language';
import { formatNumber } from '@/lib/format';

/** One plain-language sentence summarising why KAVACH landed where it did. */
export function buildVerdict(problem: Problem | undefined, decision: DecisionRecord | undefined): string {
  const cat = CATEGORY[problem?.category ?? decision?.category ?? '']?.plain ?? 'This category';

  if (decision?.outcome === 'ACTION_RECOMMENDED') {
    return `${cat}: KAVACH recommends "${decision.action_label}". The evidence (${EVIDENCE_STATUS[decision.status].plain.toLowerCase()}) cleared every eligibility check at ${decision.severity} severity.`;
  }
  if (decision?.outcome === 'CONFLICT') {
    return `${cat}: two opposite-direction problems on the same measurement cancel out, so KAVACH will not act${decision.conflict_with ? ` (conflicts with ${CATEGORY[decision.conflict_with]?.plain ?? decision.conflict_with})` : ''}.`;
  }
  if (decision?.outcome === 'MONITOR') {
    return `${cat}: there is evidence (${EVIDENCE_STATUS[decision.status].plain.toLowerCase()}), but it did not clear the bar to recommend acting. KAVACH suggests keeping watch.`;
  }
  if (decision?.outcome === 'INSUFFICIENT_SUPPORT') {
    return `${cat}: some signal exists but the support is too thin to gate an action.`;
  }
  if (problem) {
    const dir =
      typeof problem.direction === 'string' && TREND_DIRECTION[problem.direction]
        ? ` The reading is ${TREND_DIRECTION[problem.direction].plain.toLowerCase()}.`
        : '';
    const dev =
      problem.icar_deviation != null
        ? ` It sits ${formatNumber(Math.abs(problem.icar_deviation), 1)} away from the ICAR reference.`
        : '';
    return `${cat}: ${EVIDENCE_STATUS[problem.status].plain.toLowerCase()} of a problem.${dir}${dev}`;
  }
  return `${cat}: ${decision ? OUTCOME[decision.outcome].plain.toLowerCase() : 'no assessment available'}.`;
}
