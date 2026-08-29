import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { EvidenceIndicator } from './EvidenceIndicator';
import { SeverityBadge } from './SeverityBadge';
import { FeasibilityPill } from './FeasibilityPill';
import { UnavailableValue } from './UnavailableValue';
import { EligibilityCheckRow } from './EligibilityCheck';

describe('status components keep the axes distinct', () => {
  it('evidence renders plain wording + an accessible technical name', () => {
    render(<EvidenceIndicator status="no_evidence" />);
    expect(screen.getByText('No sign of a problem')).toBeInTheDocument();
    expect(screen.getByText(/no_evidence/)).toBeInTheDocument();
  });

  it('severity is independent — HIGH renders regardless of evidence', () => {
    render(<SeverityBadge severity="HIGH" />);
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('NOT_EVALUATED never says pass', () => {
    render(<FeasibilityPill status="NOT_EVALUATED" label="pump_capacity" />);
    expect(screen.getByText(/Not evaluated/)).toBeInTheDocument();
    expect(screen.queryByText(/within limits/i)).not.toBeInTheDocument();
  });

  it('missing values render as words, not zero', () => {
    const { rerender } = render(<UnavailableValue kind="unavailable" inline />);
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
    rerender(<UnavailableValue kind="unknown" inline />);
    expect(screen.getByText('Unknown')).toBeInTheDocument();
    rerender(<UnavailableValue kind="not-evaluated" inline />);
    expect(screen.getByText('Not evaluated')).toBeInTheDocument();
  });

  it('eligibility null is "Can\'t evaluate", not a pass/fail', () => {
    render(
      <ul>
        <EligibilityCheckRow check={{ name: 'severity_floor', passed: null, detail: 'n/a' }} />
      </ul>,
    );
    expect(screen.getByText(/Can't evaluate/)).toBeInTheDocument();
  });
});
