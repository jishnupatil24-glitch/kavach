/**
 * Frontend-only PROTOTYPE recovery-window estimate.
 *
 * The KAVACH backend explicitly does NOT model recovery time — see
 * app/services/optimization/effectiveness.py: "Expected outcome:
 * qualitative-direction-only, MODELED, never a recovery-time or magnitude
 * claim... the approved Phase 6 design's explicit ban on both." There is no
 * soil-moisture-response physics model anywhere in this project.
 *
 * This helper does NOT try to fill that gap with a real prediction. It
 * combines three numbers the backend already returns (severity, the
 * review-cycle cadence, and the expected direction) into a transparent,
 * clearly-labelled, low-confidence PROTOTYPE window — never a single-day
 * claim like "recovers in 4 days" — purely so the UI has something honest
 * to show instead of a blank space. It is never sent to the backend, never
 * persisted, and never presented as validated.
 */
import type { Severity } from '@/api/types';

export interface RecoveryWindow {
  lowDays: number;
  highDays: number;
  confidence: 'LOW';
  basis: string;
}

const SEVERITY_SPAN_MULTIPLIER: Partial<Record<Severity, number>> = {
  LOW: 2,
  MODERATE: 2,
  HIGH: 2.5,
  CRITICAL: 3,
};

/**
 * Returns null ("UNAVAILABLE") whenever a required input is missing —
 * never guesses a window from incomplete data.
 */
export function estimateRecoveryWindow(input: {
  severity: Severity | null | undefined;
  reviewCycleDays: number | null | undefined;
  expectedDirection: string | null | undefined;
}): RecoveryWindow | null {
  const { severity, reviewCycleDays, expectedDirection } = input;
  if (
    reviewCycleDays == null ||
    !Number.isFinite(reviewCycleDays) ||
    reviewCycleDays <= 0 ||
    !expectedDirection ||
    !severity ||
    severity === 'insufficient_data'
  ) {
    return null;
  }

  const multiplier = SEVERITY_SPAN_MULTIPLIER[severity] ?? 2;
  const lowDays = Math.round(reviewCycleDays);
  const highDays = Math.max(lowDays, Math.round(reviewCycleDays * multiplier));

  return {
    lowDays,
    highDays,
    confidence: 'LOW',
    basis:
      'Prototype estimate based on current severity, the review-cycle cadence, and the ' +
      'expected direction of the intervention — not a validated crop-physiology recovery model.',
  };
}
