import { useId } from 'react';
import { cn } from '@/lib/cn';

interface Point {
  day: number;
  value: number | null;
  reference: number | null;
}

/**
 * Tiny reference-band sparkline (hand-rolled SVG — no chart lib in cards).
 * Solid line = daily-mean sensor value; dashed = ICAR reference; the shaded
 * area between them is the deviation. Not interactive; the full
 * <VariableTrendChart> is the accessible version.
 */
export function Sparkline({
  data,
  width = 132,
  height = 40,
  className,
  ariaLabel,
}: {
  data: Point[];
  width?: number;
  height?: number;
  className?: string;
  ariaLabel: string;
}) {
  const clip = useId();
  const pts = data.filter((d) => d.value != null || d.reference != null);
  if (pts.length < 2) {
    return (
      <div
        className={cn('flex h-10 items-center text-xs text-muted', className)}
        role="img"
        aria-label={`${ariaLabel}: not enough data to chart`}
      >
        —
      </div>
    );
  }

  const xs = pts.map((d) => d.day);
  const ys = pts.flatMap((d) => [d.value, d.reference].filter((v): v is number => v != null));
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  const pad = 3;

  const sx = (x: number) => pad + ((x - minX) / spanX) * (width - pad * 2);
  const sy = (y: number) => height - pad - ((y - minY) / spanY) * (height - pad * 2);

  const line = (key: 'value' | 'reference') =>
    pts
      .filter((d) => d[key] != null)
      .map((d, i) => `${i === 0 ? 'M' : 'L'}${sx(d.day)},${sy(d[key] as number)}`)
      .join(' ');

  const band =
    pts
      .filter((d) => d.value != null && d.reference != null)
      .map((d, i) => `${i === 0 ? 'M' : 'L'}${sx(d.day)},${sy(d.value as number)}`)
      .join(' ') +
    ' ' +
    pts
      .filter((d) => d.value != null && d.reference != null)
      .reverse()
      .map((d) => `L${sx(d.day)},${sy(d.reference as number)}`)
      .join(' ') +
    ' Z';

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      role="img"
      aria-label={ariaLabel}
    >
      <clipPath id={clip}>
        <rect x="0" y="0" width={width} height={height} />
      </clipPath>
      <g clipPath={`url(#${clip})`}>
        <path d={band} fill="var(--chart-band)" stroke="none" />
        <path d={line('reference')} fill="none" stroke="var(--chart-reference)" strokeWidth="1" strokeDasharray="3 2" />
        <path d={line('value')} fill="none" stroke="var(--chart-value)" strokeWidth="1.75" />
      </g>
    </svg>
  );
}
