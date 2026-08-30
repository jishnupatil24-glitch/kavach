/**
 * Presentation-only helpers for the farmer-facing "typical application vs
 * KAVACH recommendation" comparison. All arithmetic (typical_l_per_day,
 * water_saved_vs_typical_l_per_day, etc.) is computed by the backend
 * (app/services/optimization/water_model.py) and consumed here verbatim —
 * this file only decides how to LABEL an already-computed signed number.
 * See docs/API_CONTRACT.md and docs/FRONTEND_PHASE6_NOTES.md.
 */
import { isMissing } from './format';

export type WaterImpactKind = 'saved' | 'additional' | 'equal' | 'unavailable';

export interface WaterImpactResult {
  kind: WaterImpactKind;
  /** Always a positive magnitude, or null when unavailable. */
  magnitudePerDay: number | null;
  magnitudePct: number | null;
}

/**
 * `savedVsTypicalPerDay` follows the backend's sign convention: positive =
 * typical > KAVACH (a real saving), negative = KAVACH > typical (KAVACH
 * needs MORE than typical application). Never coerce a missing/UNKNOWN
 * input into 0 — that would fabricate a "no change" result.
 */
export function classifyWaterImpact(
  savedVsTypicalPerDay: number | null,
  savedVsTypicalPct: number | null,
): WaterImpactResult {
  if (isMissing(savedVsTypicalPerDay)) {
    return { kind: 'unavailable', magnitudePerDay: null, magnitudePct: null };
  }
  if (savedVsTypicalPerDay === 0) {
    return { kind: 'equal', magnitudePerDay: 0, magnitudePct: 0 };
  }
  const kind: WaterImpactKind = savedVsTypicalPerDay > 0 ? 'saved' : 'additional';
  return {
    kind,
    magnitudePerDay: Math.abs(savedVsTypicalPerDay),
    magnitudePct: savedVsTypicalPct != null ? Math.abs(savedVsTypicalPct) : null,
  };
}
