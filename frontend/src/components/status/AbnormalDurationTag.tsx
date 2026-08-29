import type { AbnormalTier } from '@/api/types';
import { ABNORMAL_TIER } from '@/lib/plain-language';
import { CalendarClock } from 'lucide-react';
import { InfoTooltip } from '../primitives/InfoTooltip';

export function AbnormalDurationTag({
  days,
  tier,
}: {
  days: number | null;
  tier: AbnormalTier;
}) {
  if (days == null) return null;
  const t = ABNORMAL_TIER[tier];
  return (
    <span className="inline-flex items-center gap-1.5 text-sm text-body">
      <CalendarClock size={14} aria-hidden className="text-muted" />
      Abnormal for {days} {days === 1 ? 'day' : 'days'}
      <InfoTooltip
        label={`Abnormal duration basis: ${t.plain}`}
        content={
          <span>
            This count is <strong>{t.plain}</strong>.<br />
            <span className="text-xs text-muted">({t.technical})</span>
            <br />
            {t.description}
          </span>
        }
      />
    </span>
  );
}
