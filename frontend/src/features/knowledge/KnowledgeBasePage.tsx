import { useState } from 'react';
import {
  useAgronomicParameters,
  useAgronomicSources,
  useCropStages,
} from '@/api/hooks/agronomics';
import type { ParameterStatus } from '@/api/types';
import { formatNumber } from '@/lib/format';
import { PageHeader } from '@/components/primitives/PageHeader';
import { Tabs } from '@/components/primitives/Tabs';
import { EmptyState, ErrorState, SkeletonCard } from '@/components/primitives/states';

const STATUS_LABEL: Record<ParameterStatus, string> = {
  sourced: 'Cited source',
  assumption: 'Assumption',
  missing: 'Missing (no source yet)',
  source_needed: 'Value withheld pending a source',
  derived: 'Derived',
  context_dependent: 'Context-dependent',
  project_defined: 'KAVACH project-defined',
};

function ParametersTab() {
  const [status, setStatus] = useState('');
  const [domain, setDomain] = useState('');
  const q = useAgronomicParameters({
    status: status || undefined,
    domain: domain || undefined,
  });

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3">
        <label className="text-sm">
          <span className="mb-1 block font-sans font-medium text-ink">Status</span>
          <select className="input" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>
            {Object.keys(STATUS_LABEL).map((s) => (
              <option key={s} value={s}>
                {STATUS_LABEL[s as ParameterStatus]}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-sans font-medium text-ink">Domain</span>
          <input
            className="input"
            placeholder="e.g. water, nutrient"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
          />
        </label>
      </div>

      {q.isLoading ? (
        <SkeletonCard lines={6} />
      ) : q.isError ? (
        <ErrorState error={q.error} onRetry={() => q.refetch()} />
      ) : !q.data?.length ? (
        <EmptyState title="No parameters match this filter." />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-hairline">
          <table className="w-full text-left text-sm">
            <thead className="bg-surface-sunken font-sans">
              <tr>
                <th className="px-3 py-2 font-medium">Parameter</th>
                <th className="px-3 py-2 font-medium">Domain</th>
                <th className="px-3 py-2 font-medium">Value</th>
                <th className="px-3 py-2 font-medium">Unit</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Source</th>
              </tr>
            </thead>
            <tbody>
              {q.data.map((p) => {
                const value =
                  p.value_numeric != null
                    ? formatNumber(p.value_numeric, 3)
                    : p.value_min != null && p.value_max != null
                      ? `${formatNumber(p.value_min, 3)}–${formatNumber(p.value_max, 3)}`
                      : p.value_text ?? '—';
                return (
                  <tr key={p.id} className="border-t border-hairline">
                    <td className="px-3 py-2 font-mono">{p.parameter_name}</td>
                    <td className="px-3 py-2">{p.domain}</td>
                    <td className="px-3 py-2 font-mono">{value}</td>
                    <td className="px-3 py-2">{p.unit ?? '—'}</td>
                    <td className="px-3 py-2">
                      <span className="rounded-pill border border-hairline px-2 py-0.5 text-xs text-muted">
                        {STATUS_LABEL[p.status] ?? p.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-muted">{p.source_id ?? '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StagesTab() {
  const q = useCropStages();
  if (q.isLoading) return <SkeletonCard lines={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (!q.data?.length) return <EmptyState title="No crop stages recorded." />;
  return (
    <ul className="space-y-3">
      {q.data.map((s) => (
        <li key={s.id} className="card p-4">
          <p className="font-sans font-medium text-ink">{s.name.replace(/_/g, ' ')}</p>
          <p className="mt-0.5 text-sm text-muted">
            {s.start_day != null && s.end_day != null
              ? `Day ${s.start_day}–${s.end_day}`
              : 'No day mapping'}
            {s.source_id != null ? ` · source ${s.source_id}` : ''}
          </p>
          {s.description ? <p className="mt-1 text-sm text-body">{s.description}</p> : null}
        </li>
      ))}
    </ul>
  );
}

function SourcesTab() {
  const q = useAgronomicSources();
  if (q.isLoading) return <SkeletonCard lines={5} />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  if (!q.data?.length) return <EmptyState title="No sources recorded." />;
  return (
    <ul className="space-y-3">
      {q.data.map((s) => (
        <li key={s.id} className="card p-4">
          <p className="font-sans font-medium text-ink">{s.title ?? 'Untitled source'}</p>
          <p className="mt-0.5 text-sm text-muted">
            {[s.organization_or_author, s.publication_year, s.source_type]
              .filter(Boolean)
              .join(' · ')}
          </p>
          {s.document_reference ? (
            <p className="mt-1 text-xs text-muted">{s.document_reference}</p>
          ) : null}
          {s.description ? <p className="mt-1 text-sm text-body">{s.description}</p> : null}
        </li>
      ))}
    </ul>
  );
}

export function KnowledgeBasePage() {
  return (
    <>
      <PageHeader
        eyebrow="Reference"
        title="Knowledge base"
        lead="Where KAVACH's numbers come from: agronomic parameters and their sourcing status, crop stages, and the underlying sources."
      />
      <Tabs
        ariaLabel="Knowledge base sections"
        tabs={[
          { value: 'parameters', label: 'Parameters', content: <ParametersTab /> },
          { value: 'stages', label: 'Crop stages', content: <StagesTab /> },
          { value: 'sources', label: 'Sources', content: <SourcesTab /> },
        ]}
      />
    </>
  );
}
