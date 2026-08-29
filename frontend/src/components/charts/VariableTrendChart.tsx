import { useMemo } from 'react';
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TrendPoint } from './series';
import { valueOrDash } from '@/lib/format';
import type { VariableDef } from '@/lib/variables';

/**
 * One chart grammar, reused everywhere:
 *  - shaded band  = deviation between value and ICAR reference
 *  - solid line   = daily mean of sensor readings
 *  - dashed line  = ICAR reference
 * Series are distinguished by line style + direct labels, never hue alone.
 * A <details> data table is the accessible fallback.
 */
export function VariableTrendChart({
  data,
  variable,
  currentDay,
  height = 240,
}: {
  data: TrendPoint[];
  variable: VariableDef;
  currentDay?: number;
  height?: number;
}) {
  const hasData = data.some((d) => d.value != null);
  const table = useMemo(
    () => data.filter((d) => d.value != null || d.reference != null),
    [data],
  );

  if (!hasData) {
    return (
      <p className="rounded border border-dashed border-hairline p-4 text-sm text-muted">
        Not enough sensor history to chart {variable.plain.toLowerCase()} yet.
      </p>
    );
  }

  return (
    <figure className="m-0">
      <figcaption className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-[2px] w-4" style={{ background: 'var(--chart-value)' }} />
          Daily mean of sensor readings
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span
            className="inline-block h-[2px] w-4"
            style={{
              backgroundImage:
                'repeating-linear-gradient(to right, var(--chart-reference) 0 4px, transparent 4px 7px)',
            }}
          />
          ICAR reference
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block h-3 w-4" style={{ background: 'var(--chart-band)' }} />
          Deviation
        </span>
        <span className="ml-auto font-mono">{variable.unit}</span>
      </figcaption>

      <div className="w-full overflow-x-auto">
        <div style={{ minWidth: 360, height }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
              <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
              <XAxis
                dataKey="day"
                tick={{ fontSize: 11, fill: 'rgb(var(--muted))' }}
                tickLine={false}
                axisLine={{ stroke: 'var(--chart-grid)' }}
              />
              <YAxis
                width={44}
                tick={{ fontSize: 11, fill: 'rgb(var(--muted))' }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgb(var(--surface))',
                  border: '1px solid rgb(var(--border-hairline))',
                  borderRadius: 10,
                  fontSize: 12,
                }}
                labelFormatter={(d) => `Day ${d}`}
                formatter={(value, name) => {
                  if (Array.isArray(value)) return ['', ''] as [string, string];
                  const n = typeof value === 'number' ? value : Number(value);
                  const label = name === 'value' ? 'Sensor mean' : 'ICAR reference';
                  return [`${valueOrDash(n, variable.precision)} ${variable.unit}`, label] as [
                    string,
                    string,
                  ];
                }}
              />
              <Area
                type="monotone"
                dataKey="band"
                stroke="none"
                fill="var(--chart-band)"
                isAnimationActive={false}
                connectNulls
              />
              <Line
                type="monotone"
                dataKey="reference"
                stroke="var(--chart-reference)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                dot={false}
                isAnimationActive={false}
                connectNulls
                name="reference"
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--chart-value)"
                strokeWidth={2}
                dot={{ r: 2 }}
                activeDot={{ r: 4 }}
                isAnimationActive={false}
                connectNulls
                name="value"
              />
              {currentDay != null ? (
                <ReferenceLine x={currentDay} stroke="rgb(var(--muted))" strokeDasharray="2 2" />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      <details className="mt-3 text-sm">
        <summary className="cursor-pointer font-sans text-brand-700">
          Show data as a table
        </summary>
        <div className="mt-2 max-h-64 overflow-auto rounded border border-hairline">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-surface-sunken">
              <tr>
                <th className="px-3 py-1.5 font-sans font-medium">Day</th>
                <th className="px-3 py-1.5 font-sans font-medium">Sensor mean ({variable.unit})</th>
                <th className="px-3 py-1.5 font-sans font-medium">ICAR reference ({variable.unit})</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {table.map((d) => (
                <tr key={d.day} className="border-t border-hairline">
                  <td className="px-3 py-1">{d.day}</td>
                  <td className="px-3 py-1">{valueOrDash(d.value, variable.precision)}</td>
                  <td className="px-3 py-1">{valueOrDash(d.reference, variable.precision)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
