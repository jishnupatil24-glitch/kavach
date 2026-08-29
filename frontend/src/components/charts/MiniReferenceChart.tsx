import {
  Area,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { TrendPoint } from './series';
import { valueOrDash } from '@/lib/format';

/** Compact value-vs-reference chart for the reasoning panel. */
export function MiniReferenceChart({
  data,
  unit,
  precision = 1,
  height = 120,
  ariaLabel,
}: {
  data: TrendPoint[];
  unit: string;
  precision?: number;
  height?: number;
  ariaLabel: string;
}) {
  const hasData = data.some((d) => d.value != null);
  if (!hasData) {
    return <p className="text-xs text-muted">Not enough history to chart.</p>;
  }
  return (
    <div className="w-full overflow-x-auto" role="img" aria-label={ariaLabel}>
      <div style={{ minWidth: 260, height }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <XAxis dataKey="day" tick={{ fontSize: 10, fill: 'rgb(var(--muted))' }} tickLine={false} axisLine={false} />
            <YAxis width={34} tick={{ fontSize: 10, fill: 'rgb(var(--muted))' }} tickLine={false} axisLine={false} />
            <Tooltip
              contentStyle={{
                background: 'rgb(var(--surface))',
                border: '1px solid rgb(var(--border-hairline))',
                borderRadius: 8,
                fontSize: 11,
              }}
              labelFormatter={(d) => `Day ${d}`}
              formatter={(value, name) => {
                if (Array.isArray(value)) return ['', ''] as [string, string];
                const n = typeof value === 'number' ? value : Number(value);
                return [
                  `${valueOrDash(n, precision)} ${unit}`,
                  name === 'value' ? 'Sensor mean' : 'ICAR',
                ] as [string, string];
              }}
            />
            <Area dataKey="band" stroke="none" fill="var(--chart-band)" isAnimationActive={false} connectNulls />
            <Line
              dataKey="reference"
              stroke="var(--chart-reference)"
              strokeWidth={1.25}
              strokeDasharray="4 3"
              dot={false}
              isAnimationActive={false}
              connectNulls
              name="reference"
            />
            <Line
              dataKey="value"
              stroke="var(--chart-value)"
              strokeWidth={1.75}
              dot={false}
              isAnimationActive={false}
              connectNulls
              name="value"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
