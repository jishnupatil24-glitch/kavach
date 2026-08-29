/**
 * Single source of truth for turning backend enum values and field names into
 * plain language. Plain wording is the PRIMARY UI label everywhere; the
 * `technical` string is shown secondarily (subtitle / tooltip) so the mapping
 * stays honest and traceable to docs/API_CONTRACT.md.
 *
 * Nothing here changes backend meaning — it only renames it for a farmer/judge.
 */

export interface Term {
  plain: string;
  technical: string;
  description: string;
}

function t(plain: string, technical: string, description: string): Term {
  return { plain, technical, description };
}

/* ---- Phase 4: evidence status (monochrome "signal strength" axis) ---- */
export const EVIDENCE_STATUS: Record<string, Term> = {
  insufficient_data: t(
    'Not enough data',
    'insufficient_data',
    'Too few readings so far to say anything about this category.',
  ),
  no_evidence: t(
    'No sign of a problem',
    'no_evidence',
    'The readings do not point to a problem in this category.',
  ),
  weak_evidence: t(
    'Some signs',
    'weak_evidence',
    'One indicator points to a possible problem, but it is not corroborated.',
  ),
  corroborated_evidence: t(
    'Confirmed by multiple signals',
    'corroborated_evidence',
    'Several independent indicators agree that this category is abnormal.',
  ),
};

/* ---- Phase 4/5: severity (hue ramp — "how bad", independent of evidence) ---- */
export const SEVERITY: Record<string, Term> = {
  insufficient_data: t('Not scored', 'insufficient_data', 'Not enough data to score severity.'),
  LOW: t('Low', 'LOW', 'A deterministic observational severity score in the lowest band.'),
  MODERATE: t('Moderate', 'MODERATE', 'A deterministic observational severity score in the middle band.'),
  HIGH: t('High', 'HIGH', 'A deterministic observational severity score in a high band.'),
  CRITICAL: t('Critical', 'CRITICAL', 'A deterministic observational severity score in the top band.'),
};

/* ---- Phase 5: decision outcome ---- */
export const OUTCOME: Record<string, Term> = {
  ACTION_RECOMMENDED: t(
    'Action recommended',
    'ACTION_RECOMMENDED',
    'The problem cleared every eligibility check, so KAVACH recommends acting.',
  ),
  MONITOR: t(
    'Keep watching',
    'MONITOR',
    'There is evidence, but it did not clear the bar to recommend acting yet.',
  ),
  NO_ACTION: t('No action needed', 'NO_ACTION', 'No sufficient evidence of a problem in this category.'),
  INSUFFICIENT_SUPPORT: t(
    'Not enough support to act',
    'INSUFFICIENT_SUPPORT',
    'Some signal exists but the support is too thin to gate an action.',
  ),
  CONFLICT: t(
    'Conflicting signals',
    'CONFLICT',
    'Two opposite-direction problems on the same measurement cancel out — KAVACH will not act.',
  ),
};

/* ---- Provenance — attached to every number ---- */
export const PROVENANCE: Record<string, Term> = {
  SOURCED: t(
    'Cited agronomic source',
    'SOURCED',
    'A value taken directly from a documented external source (highest confidence).',
  ),
  PROJECT_DEFINED: t(
    'KAVACH assumption — not validated',
    'PROJECT_DEFINED',
    'A KAVACH prototype assumption. Explicitly not a scientifically validated agronomic prescription.',
  ),
  MODELED: t(
    'Calculated by KAVACH',
    'MODELED',
    'A deterministic calculation combining the inputs above — not measured, not sourced.',
  ),
  'MODELED EXPECTED DIRECTION': t(
    'Calculated by KAVACH',
    'MODELED EXPECTED DIRECTION',
    'The direction KAVACH expects the reading to move if the plan is followed — modelled, not measured.',
  ),
};

/* ---- Phase 3: trend direction ---- */
export const TREND_DIRECTION: Record<string, Term> = {
  RISING: t('Rising', 'RISING', 'Ordinary-least-squares slope is significantly positive.'),
  FALLING: t('Falling', 'FALLING', 'Ordinary-least-squares slope is significantly negative.'),
  STABLE: t('Steady', 'STABLE', 'Slope is within the noise-derived stability band.'),
  UNDETERMINED: t('Unclear', 'UNDETERMINED', 'Not enough signal to call a direction.'),
};

/* ---- Phase 6: feasibility + cost + population source ---- */
export const FEASIBILITY: Record<string, Term> = {
  PASS: t('Within limits', 'PASS', 'The required volume fits the configured resource limit.'),
  FAIL: t('Over the limit', 'FAIL', 'The required volume exceeds the configured resource limit.'),
  NOT_EVALUATED: t(
    'Not evaluated',
    'NOT_EVALUATED',
    'A required input (resource limit or plant population) is missing, so this was not checked. This is NOT a pass.',
  ),
};

export const COST_STATUS: Record<string, Term> = {
  AVAILABLE: t('Costed', 'AVAILABLE', 'A cost rate is configured, so a cost figure was produced.'),
  UNAVAILABLE: t(
    'Cost unavailable',
    'UNAVAILABLE',
    'No cost rate is configured (or a required quantity is missing), so no cost figure exists.',
  ),
};

export const POPULATION_SOURCE: Record<string, Term> = {
  PROVIDED: t('From your setup', 'PROVIDED', 'Plant population you entered in Farm Setup.'),
  ESTIMATED: t('Estimated from spacing', 'ESTIMATED', 'Derived from field area and plant/row spacing.'),
  UNKNOWN: t(
    'Unknown',
    'UNKNOWN',
    'No plant population and no spacing — whole-field totals cannot be computed.',
  ),
};

export const ABNORMAL_TIER: Record<string, Term> = {
  sourced_threshold: t(
    'measured against a cited threshold',
    'sourced_threshold',
    'Abnormal days counted against a documented agronomic boundary.',
  ),
  icar_sign_trend_proxy: t(
    'inferred from reference deviation + trend',
    'icar_sign_trend_proxy',
    'No sourced threshold exists; abnormal days inferred from the sign of the ICAR deviation and the trend direction.',
  ),
};

/* ---- Phase 4: the 10 fixed problem categories ---- */
export const CATEGORY: Record<string, Term> = {
  water_depletion: t('Water shortage in the soil', 'water_depletion', 'Soil moisture running low.'),
  excessive_moisture: t('Too much moisture in the soil', 'excessive_moisture', 'Soil moisture running high.'),
  heat_related: t('Heat stress', 'heat_related', 'Temperature above a safe band.'),
  temperature_deficit: t('Too cold', 'temperature_deficit', 'Temperature below a safe band.'),
  humidity_low: t('Air too dry', 'humidity_low', 'Relative humidity below the sourced band.'),
  humidity_high: t('Air too humid', 'humidity_high', 'Relative humidity above the sourced band.'),
  nitrogen_related: t('Low nitrogen', 'nitrogen_related', 'Soil nitrogen below demand.'),
  phosphorus_related: t('Low phosphorus', 'phosphorus_related', 'Soil phosphorus below demand.'),
  potassium_related: t('Low potassium', 'potassium_related', 'Soil potassium below demand.'),
  light_deficit: t('Not enough light', 'light_deficit', 'Daily light integral below target.'),
};

/* ---- Phase 2: scenarios ---- */
export const SCENARIO: Record<string, Term> = {
  normal: t('Normal conditions', 'normal', 'No injected stress.'),
  heatwave: t('Heatwave', 'heatwave', 'A sustained temperature spike over a window.'),
  water_shortage: t('Water shortage', 'water_shortage', 'Reduced irrigation over a window.'),
  excess_irrigation: t('Over-irrigation', 'excess_irrigation', 'Excess irrigation over a window.'),
  high_humidity: t('High humidity', 'high_humidity', 'Elevated humidity over a window.'),
};

export const SEVERITY_INPUT: Record<string, string> = {
  mild: 'Mild',
  moderate: 'Moderate',
  severe: 'Severe',
};

/* ---- helper: look up with a safe fallback ---- */
export function term(map: Record<string, Term>, key: string | null | undefined): Term {
  if (key && map[key]) return map[key];
  const k = key ?? 'unknown';
  return t(k.replace(/[_-]+/g, ' '), k, '');
}
