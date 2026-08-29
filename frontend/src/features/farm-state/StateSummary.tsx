import type { StateAnalysis } from '@/api/types';
import { variableByField } from '@/lib/variables';
import { TREND_DIRECTION } from '@/lib/plain-language';

/**
 * One plain-language sentence about the day, composed only from Phase 3 fields
 * (no new logic): which variables are moving and away from the reference.
 */
export function StateSummary({ analysis }: { analysis: StateAnalysis }) {
  const notable = analysis.parameters
    .filter((p) => p.trend.direction === 'RISING' || p.trend.direction === 'FALLING')
    .sort((a, b) => b.persistence.days - a.persistence.days)
    .slice(0, 3)
    .map((p) => {
      const name = variableByField(p.current.field)?.plain ?? p.current.parameter;
      return `${name.toLowerCase()} is ${TREND_DIRECTION[p.trend.direction].plain.toLowerCase()}`;
    });

  const stages = analysis.crop_stages.map((s) => s.name.replace(/_/g, ' ')).join(', ');

  return (
    <div className="mb-8 rounded-lg border border-hairline bg-surface p-5">
      <p className="text-base text-body">
        {notable.length
          ? `On day ${analysis.analysis_day}, ${joinWithAnd(notable)}.`
          : `On day ${analysis.analysis_day}, every tracked variable is steady.`}
      </p>
      {stages ? (
        <p className="mt-1 text-sm text-muted">
          Crop stage: {stages} · run length {analysis.duration_days} days
        </p>
      ) : null}
    </div>
  );
}

function joinWithAnd(items: string[]): string {
  if (items.length <= 1) return items[0] ?? '';
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`;
}
