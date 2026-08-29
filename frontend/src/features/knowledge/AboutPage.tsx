import type { ReactNode } from 'react';
import type { EvidenceStatus, Outcome, Severity } from '@/api/types';
import { PageHeader } from '@/components/primitives/PageHeader';
import { EvidenceIndicator } from '@/components/status/EvidenceIndicator';
import { SeverityBadge } from '@/components/status/SeverityBadge';
import { OutcomeBadge } from '@/components/status/OutcomeBadge';
import { FeasibilityPill } from '@/components/status/FeasibilityPill';
import { ProvenanceLegend } from '@/components/status/Provenance';
import { UnavailableValue } from '@/components/status/UnavailableValue';
import {
  EVIDENCE_STATUS,
  OUTCOME,
  SEVERITY,
} from '@/lib/plain-language';

const EVIDENCE: EvidenceStatus[] = [
  'insufficient_data',
  'no_evidence',
  'weak_evidence',
  'corroborated_evidence',
];
const SEV: Severity[] = ['insufficient_data', 'LOW', 'MODERATE', 'HIGH', 'CRITICAL'];
const OUTC: Outcome[] = [
  'ACTION_RECOMMENDED',
  'MONITOR',
  'NO_ACTION',
  'INSUFFICIENT_SUPPORT',
  'CONFLICT',
];

export function AboutPage() {
  return (
    <>
      <PageHeader
        eyebrow="Reference"
        title="How to read KAVACH"
        lead="KAVACH keeps several ideas deliberately separate. Here is what each visual means."
      />

      <div className="space-y-10">
        <Section
          title="Evidence — how sure KAVACH is"
          body="An independent axis from severity. Shown as monochrome signal bars, never colour. A category with no evidence of a problem can still carry a non-trivial severity score — the two never merge."
        >
          <ul className="space-y-3">
            {EVIDENCE.map((s) => (
              <li key={s} className="flex flex-wrap items-center gap-4">
                <EvidenceIndicator status={s} />
                <span className="text-sm text-muted">{EVIDENCE_STATUS[s].description}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section
          title="Severity — how bad it looks"
          body="A deterministic observational score, banded LOW to CRITICAL. It is not itself an agronomic diagnosis, and its bands are not sourced thresholds."
        >
          <ul className="space-y-3">
            {SEV.map((s) => (
              <li key={s} className="flex flex-wrap items-center gap-4">
                <SeverityBadge severity={s} />
                <span className="text-sm text-muted">{SEVERITY[s].description}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section
          title="Outcome — what the decision engine decided"
          body="The result of gating an evidenced problem through eligibility checks and conflict detection."
        >
          <ul className="space-y-3">
            {OUTC.map((o) => (
              <li key={o} className="flex flex-wrap items-center gap-4">
                <OutcomeBadge outcome={o} priority={o === 'ACTION_RECOMMENDED' ? 1 : null} />
                <span className="text-sm text-muted">{OUTCOME[o].description}</span>
              </li>
            ))}
          </ul>
        </Section>

        <Section
          title="Provenance — where a number comes from"
          body="Attached to every measured value in the Optimized Plan."
        >
          <ProvenanceLegend />
        </Section>

        <Section
          title="Feasibility — three distinct states"
          body="NOT_EVALUATED is not a pass. It means a required input was missing, so the check did not run."
        >
          <div className="flex flex-wrap gap-3">
            <FeasibilityPill status="PASS" label="available_water" />
            <FeasibilityPill status="FAIL" label="available_water" />
            <FeasibilityPill status="NOT_EVALUATED" label="pump_capacity" />
          </div>
        </Section>

        <Section
          title="Missing data — never shown as zero"
          body="Three separate meanings, each rendered distinctly and never as 0, blank, or green."
        >
          <div className="space-y-3">
            <UnavailableValue
              kind="unavailable"
              why="The backend withheld this value (for example, no baseline exists for this crop stage, or no cost rate is configured)."
            />
            <UnavailableValue
              kind="unknown"
              why="Plant population is not set and cannot be estimated, so whole-field totals cannot be produced."
            />
            <UnavailableValue
              kind="not-evaluated"
              why="A feasibility check could not run because a resource limit was not configured."
            />
          </div>
        </Section>
      </div>
    </>
  );
}

function Section({
  title,
  body,
  children,
}: {
  title: string;
  body: string;
  children: ReactNode;
}) {
  return (
    <section className="card p-6">
      <h2 className="font-sans text-lg font-semibold text-ink">{title}</h2>
      <p className="mt-1 mb-4 max-w-2xl text-sm text-body">{body}</p>
      {children}
    </section>
  );
}
