import { Link } from 'react-router-dom';
import { useRunContext } from '@/context/RunContext';
import { useObservations } from '@/api/hooks/pipeline';
import { VARIABLES } from '@/lib/variables';
import { formatNumber } from '@/lib/format';
import { PageHeader } from '@/components/primitives/PageHeader';
import { DayOutOfRangeNotice } from '@/components/primitives/DayOutOfRangeNotice';
import { EmptyState, ErrorState, SkeletonCard } from '@/components/primitives/states';

/** Raw 6-hour sensor observations for the selected day. Secondary view. */
export function SensorsPage() {
  const { runId, day, dayOutOfRange, durationDays } = useRunContext();
  const q = useObservations({ runId, day, enabled: !dayOutOfRange });

  return (
    <>
      <PageHeader
        eyebrow="Reference"
        title={`Raw sensor readings — day ${day}`}
        lead="The unprocessed 6-hour observations for this day."
      />
      <p className="mb-6 text-sm text-muted">
        Raw readings — see{' '}
        <Link to={`/runs/${runId}/state?day=${day}`} className="text-brand-700 underline">
          Farm State
        </Link>{' '}
        for the analysed view.
      </p>

      {dayOutOfRange ? (
        <DayOutOfRangeNotice max={durationDays} />
      ) : q.isLoading ? (
        <SkeletonCard lines={6} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} />
      ) : !q.data?.length ? (
        <EmptyState title={`No observations recorded for day ${day}.`} />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-surface-sunken font-sans">
              <tr>
                <th className="px-3 py-2 font-medium">Hour</th>
                {VARIABLES.map((v) => (
                  <th key={v.key} className="px-3 py-2 font-medium">
                    {v.short} <span className="font-normal text-muted">({v.unit})</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="font-mono">
              {q.data.map((o) => (
                <tr key={o.id} className="border-t border-hairline">
                  <td className="px-3 py-2">{String(o.hour).padStart(2, '0')}:00</td>
                  {VARIABLES.map((v) => (
                    <td key={v.key} className="px-3 py-2">
                      {formatNumber(o[v.observationKey] as number, v.precision)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
