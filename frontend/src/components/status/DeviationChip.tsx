import { formatSigned } from '@/lib/format';
import { cn } from '@/lib/cn';

/**
 * Signed deviation from the ICAR reference. Neutral styling — direction of the
 * deviation is not itself "good" or "bad" (that is the assessment's job), so no
 * red/green here. Just the sign and magnitude.
 */
export function DeviationChip({
  value,
  unitSuffix,
  className,
}: {
  value: number | null;
  unitSuffix?: string | null;
  className?: string;
}) {
  if (value == null) {
    return <span className={cn('text-xs italic text-muted', className)}>no reference</span>;
  }
  const s = formatSigned(value, 1);
  const unit = (unitSuffix ?? '').trim();
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-sm border border-hairline bg-surface-sunken px-1.5 py-0.5 font-mono text-xs text-body',
        className,
      )}
      title="Difference from the ICAR reference for this day"
    >
      {s}
      {unit ? ` ${unit}` : ''} vs reference
    </span>
  );
}
