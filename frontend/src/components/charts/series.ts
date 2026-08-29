import type { SensorObservation, TomatoReferenceProfile } from '@/api/types';
import type { VariableDef } from '@/lib/variables';

export interface TrendPoint {
  day: number;
  value: number | null;
  reference: number | null;
  /** [min(value,ref), max(value,ref)] for the deviation band area. */
  band: [number, number] | null;
}

/**
 * Daily mean of the raw sensor observations for one variable, aligned with the
 * ICAR reference series. This is real data — labelled "daily mean of sensor
 * readings" in the UI — not a fabricated analysed time series.
 */
export function buildTrendSeries(
  observations: SensorObservation[] | undefined,
  reference: TomatoReferenceProfile[] | undefined,
  variable: VariableDef,
  maxDay?: number,
): TrendPoint[] {
  const byDay = new Map<number, number[]>();
  for (const o of observations ?? []) {
    if (maxDay != null && o.day > maxDay) continue;
    const v = o[variable.observationKey] as number;
    if (typeof v !== 'number' || Number.isNaN(v)) continue;
    const arr = byDay.get(o.day) ?? [];
    arr.push(v);
    byDay.set(o.day, arr);
  }

  const refByDay = new Map<number, number>();
  for (const r of reference ?? []) {
    refByDay.set(r.day, r[variable.referenceKey] as number);
  }

  const days = Array.from(
    new Set<number>([...byDay.keys(), ...(maxDay != null ? [] : refByDay.keys())]),
  ).sort((a, b) => a - b);

  const upTo = maxDay ?? (days.length ? days[days.length - 1] : 0);

  return days
    .filter((d) => d <= upTo)
    .map((day) => {
      const vs = byDay.get(day);
      const value = vs && vs.length ? vs.reduce((s, x) => s + x, 0) / vs.length : null;
      const reference = refByDay.get(day) ?? null;
      const band: [number, number] | null =
        value != null && reference != null
          ? [Math.min(value, reference), Math.max(value, reference)]
          : null;
      return { day, value, reference, band };
    });
}
