/**
 * Number formatting for KAVACH.
 *
 * The single rule: a value the backend withheld (`null`) is NEVER rendered as
 * 0, blank, or a guess. Call `isMissing` / `valueOrDash` before formatting, and
 * render the distinct missing states (Unavailable / Unknown / Not evaluated) via
 * the <UnavailableValue> component, not here.
 */

export type Maybe<T> = T | null | undefined;

export function isMissing(v: unknown): v is null | undefined {
  return v === null || v === undefined || (typeof v === 'number' && Number.isNaN(v));
}

/** Locale number with a sensible max precision. Returns `null` if missing. */
export function formatNumber(v: Maybe<number>, maxFractionDigits = 2): string | null {
  if (isMissing(v)) return null;
  return new Intl.NumberFormat('en', {
    maximumFractionDigits: maxFractionDigits,
  }).format(v);
}

/** Formats a value, or an em-dash placeholder when missing (for dense tables). */
export function valueOrDash(v: Maybe<number>, maxFractionDigits = 2): string {
  return formatNumber(v, maxFractionDigits) ?? '—';
}

export function formatWithUnit(v: Maybe<number>, unit: string, maxFractionDigits = 2): string | null {
  const n = formatNumber(v, maxFractionDigits);
  if (n === null) return null;
  const sep = unit.startsWith('%') || unit.startsWith('°') ? '' : ' ';
  return `${n}${sep}${unit}`;
}

/** Signed number, e.g. "+3.2" / "-1.0". Missing -> null. */
export function formatSigned(v: Maybe<number>, maxFractionDigits = 2): string | null {
  if (isMissing(v)) return null;
  const n = formatNumber(Math.abs(v), maxFractionDigits);
  return `${v > 0 ? '+' : v < 0 ? '-' : ''}${n}`;
}

export function formatPercent(v: Maybe<number>, maxFractionDigits = 1): string | null {
  if (isMissing(v)) return null;
  return `${formatNumber(v, maxFractionDigits)}%`;
}

/** "0.8 pp/day", keeps the backend-supplied rate unit verbatim. */
export function formatRate(v: Maybe<number>, unit: Maybe<string>): string | null {
  if (isMissing(v)) return null;
  const n = formatSigned(v, 2);
  return unit ? `${n} ${unit}` : n;
}

/** Human date from an ISO string. */
export function formatDate(iso: Maybe<string>): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('en', { year: 'numeric', month: 'short', day: 'numeric' });
}

export function titleCase(s: string): string {
  return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
