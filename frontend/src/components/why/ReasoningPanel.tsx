import { useMemo } from 'react';
import type { ProblemCategory } from '@/api/types';
import { useAnalysis, useAssessment, useDecision, useObservations } from '@/api/hooks/pipeline';
import { useReferenceProfile } from '@/api/hooks/reference';
import { variableByField } from '@/lib/variables';
import {
  ABNORMAL_TIER,
  CATEGORY,
  EVIDENCE_STATUS,
  PROVENANCE,
} from '@/lib/plain-language';
import { formatNumber, formatRate, formatWithUnit } from '@/lib/format';
import { Sheet } from '@/components/primitives/Sheet';
import { EvidenceIndicator } from '@/components/status/EvidenceIndicator';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { OutcomeBadge } from '@/components/status/OutcomeBadge';
import { EligibilityChecklist } from '@/components/status/EligibilityCheck';
import { MiniReferenceChart } from '@/components/charts/MiniReferenceChart';
import { buildTrendSeries } from '@/components/charts/series';
import { buildVerdict } from './reasoning';

/**
 * Shared "Why did KAVACH say this?" panel. Same component for Problems and
 * Recommendations — the Decision-logic section simply populates more fully when
 * a decision record exists.
 */
export function ReasoningPanel({
  open,
  onOpenChange,
  category,
  runId,
  day,
}: {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  category: ProblemCategory;
  runId: number;
  day: number;
}) {
  const assessment = useAssessment({ runId, day, enabled: open });
  const decision = useDecision({ runId, day, enabled: open });
  const analysis = useAnalysis({ runId, day, enabled: open });
  const observations = useObservations({ runId, day: null, enabled: open });
  const reference = useReferenceProfile();

  const problem = assessment.data?.problems.find((p) => p.category === category);
  const record = decision.data?.decisions.find((d) => d.category === category);
  const param = analysis.data?.parameters.find(
    (p) => p.current.field === problem?.field || p.current.parameter === category,
  );
  const variable = variableByField(problem?.field ?? param?.current.field);

  const series = useMemo(() => {
    if (!variable) return [];
    return buildTrendSeries(observations.data, reference.data, variable, day);
  }, [variable, observations.data, reference.data, day]);

  const loading = assessment.isLoading || decision.isLoading;
  const catName = CATEGORY[category]?.plain ?? category;

  return (
    <Sheet
      open={open}
      onOpenChange={onOpenChange}
      size="lg"
      title="Why did KAVACH say this?"
      description={`${catName} · day ${day}`}
    >
      {loading ? (
        <p className="text-sm text-muted">Loading the reasoning…</p>
      ) : (
        <div className="space-y-8">
          {/* Verdict */}
          <section>
            <SectionLabel>Verdict</SectionLabel>
            <p className="text-base text-body">{buildVerdict(problem, record)}</p>
          </section>

          {/* The signals */}
          <section>
            <SectionLabel>The signals (state analysis)</SectionLabel>
            {param ? (
              <div className="space-y-3">
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
                  <Row
                    label="Current value"
                    value={formatWithUnit(param.current.value, variable?.unit ?? '', variable?.precision ?? 1)}
                  />
                  <Row
                    label="ICAR reference"
                    value={formatWithUnit(param.icar.icar_value, variable?.unit ?? '', variable?.precision ?? 1)}
                  />
                  <Row label="Trend" value={`${param.trend.direction}`} />
                  <Row
                    label="Rate of change"
                    value={formatRate(param.trend.rate_per_day, param.trend.rate_unit)}
                  />
                  <Row
                    label="Regression noise (±/day)"
                    value={formatNumber(param.trend.standard_error_per_day, 3)}
                  />
                  <Row
                    label="Persistence"
                    value={`${param.persistence.days} ${param.persistence.days === 1 ? 'day' : 'days'} ${param.persistence.direction.toLowerCase()}`}
                  />
                </dl>
                {variable ? (
                  <MiniReferenceChart
                    data={series}
                    unit={variable.unit}
                    precision={variable.precision}
                    ariaLabel={`${variable.plain}: daily mean sensor reading versus ICAR reference up to day ${day}`}
                  />
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-muted">No per-variable analysis available for this day.</p>
            )}
          </section>

          {/* Evidence assessment */}
          {problem ? (
            <section>
              <SectionLabel>Evidence assessment</SectionLabel>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
                  <EvidenceIndicator status={problem.status} />
                  <SeverityBadge severity={problem.severity} />
                </div>
                <p className="text-xs text-muted">
                  Evidence and severity are independent axes — {EVIDENCE_STATUS[problem.status].plain.toLowerCase()}{' '}
                  can still carry a non-trivial severity.
                </p>

                {problem.sourced_corroboration_notes.length > 0 && (
                  <NoteList title="Corroboration notes" items={problem.sourced_corroboration_notes} />
                )}

                {problem.severity_factors ? (
                  <div>
                    <p className="mb-1 font-sans font-medium text-ink">Severity factors</p>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
                      <Row label="Deviation ratio" value={formatNumber(problem.severity_factors.deviation_ratio, 2)} />
                      <Row label="Deviation score" value={String(problem.severity_factors.deviation_score)} />
                      <Row label="Intensity ratio" value={formatNumber(problem.severity_factors.intensity_ratio, 2)} />
                      <Row label="Intensity score" value={String(problem.severity_factors.intensity_score)} />
                      <Row label="Duration fraction" value={formatNumber(problem.severity_factors.duration_fraction, 2)} />
                      <Row label="Duration score" value={String(problem.severity_factors.duration_score)} />
                      <Row label="Total score" value={String(problem.severity_factors.total_score)} />
                    </dl>
                  </div>
                ) : (
                  <p className="text-xs text-muted">Severity factors: not scored (insufficient data).</p>
                )}

                <p>
                  <span className="font-sans font-medium text-ink">Abnormal duration: </span>
                  {problem.abnormal_state_duration.days}{' '}
                  {problem.abnormal_state_duration.days === 1 ? 'day' : 'days'} —{' '}
                  {ABNORMAL_TIER[problem.abnormal_state_duration.tier].plain}{' '}
                  <span className="text-xs text-muted">
                    ({problem.abnormal_state_duration.tier})
                  </span>
                </p>
                <p className="text-xs italic text-muted">{problem.abnormal_state_duration.provenance_note}</p>

                <NoteList title="Raw sensor range" items={[problem.raw_range.label]} />
              </div>
            </section>
          ) : null}

          {/* Decision logic */}
          {record ? (
            <section>
              <SectionLabel>Decision logic</SectionLabel>
              <div className="space-y-3 text-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <OutcomeBadge outcome={record.outcome} priority={record.priority} />
                  {record.conflict_with ? (
                    <span className="text-xs text-sev-high">
                      Conflicts with {CATEGORY[record.conflict_with]?.plain ?? record.conflict_with}
                    </span>
                  ) : null}
                </div>
                <div>
                  <p className="mb-1 font-sans font-medium text-ink">Eligibility checks</p>
                  <EligibilityChecklist checks={record.eligibility_checks} />
                </div>
                {record.priority != null ? (
                  <p>
                    <span className="font-sans font-medium text-ink">Priority #{record.priority}: </span>
                    {record.priority_reason}
                  </p>
                ) : null}
                <p className="text-body">{record.action_basis}</p>
              </div>
            </section>
          ) : null}

          {/* Provenance & limits */}
          <section>
            <SectionLabel>Provenance &amp; limits</SectionLabel>
            <div className="space-y-3 text-sm">
              {record ? (
                <p>
                  <span className="font-sans font-medium text-ink">Decision provenance: </span>
                  {PROVENANCE[record.decision_provenance]?.plain ?? record.decision_provenance}{' '}
                  <span className="text-xs text-muted">({record.decision_provenance})</span>
                </p>
              ) : null}
              {problem?.provenance_notes.length ? (
                <NoteList title="Provenance notes" items={problem.provenance_notes} />
              ) : null}
              {problem ? (
                <p className="text-xs italic text-muted">{problem.severity_disclaimer}</p>
              ) : null}
              {record?.limitations.length ? (
                <NoteList title="Limitations" items={record.limitations} />
              ) : null}
            </div>
          </section>
        </div>
      )}
    </Sheet>
  );
}

function SectionLabel({ children }: { children: string }) {
  return (
    <h3 className="mb-2 font-sans text-xs font-semibold uppercase tracking-wide text-brand-700">
      {children}
    </h3>
  );
}

function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <>
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-mono text-ink">{value ?? '—'}</dd>
    </>
  );
}

function NoteList({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="mb-1 font-sans font-medium text-ink">{title}</p>
      <ul className="list-disc space-y-1 pl-5 text-body">
        {items.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}
