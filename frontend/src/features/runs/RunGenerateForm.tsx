import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useCreateRun } from '@/api/hooks/runs';
import type { Scenario, SeverityInput, SimulationRunCreate } from '@/api/types';
import { SCENARIO, SEVERITY_INPUT } from '@/lib/plain-language';
import { Button } from '@/components/primitives/Button';
import { ErrorState } from '@/components/primitives/states';

const SCENARIOS: Scenario[] = [
  'normal',
  'water_shortage',
  'excess_irrigation',
  'heatwave',
  'high_humidity',
];
const SEVERITIES: SeverityInput[] = ['mild', 'moderate', 'severe'];

interface Errors {
  [k: string]: string | undefined;
}

export function RunGenerateForm({ onCreated }: { onCreated: (runId: number) => void }) {
  const create = useCreateRun();
  const [duration, setDuration] = useState(38);
  const [scenario, setScenario] = useState<Scenario>('water_shortage');
  const [seed, setSeed] = useState(() => Math.floor(Math.random() * 900000) + 1000);
  const [severity, setSeverity] = useState<SeverityInput>('severe');
  const [startDay, setStartDay] = useState(2);
  const [windowLen, setWindowLen] = useState(25);

  const isNormal = scenario === 'normal';

  const errors = useMemo<Errors>(() => {
    const e: Errors = {};
    if (duration < 1 || duration > 120) e.duration = 'Duration must be between 1 and 120 days.';
    if (!isNormal) {
      if (startDay < 1 || startDay > duration)
        e.startDay = `Start day must be between 1 and ${duration}.`;
      if (windowLen < 1 || startDay + windowLen - 1 > duration)
        e.windowLen = 'The stress window must fit inside the run.';
    }
    return e;
  }, [duration, isNormal, startDay, windowLen]);

  const valid = Object.keys(errors).length === 0;

  const submit = () => {
    if (!valid) return;
    const body: SimulationRunCreate = {
      duration_days: duration,
      scenario,
      seed,
      severity: isNormal ? null : severity,
      scenario_start_day: isNormal ? null : startDay,
      scenario_duration_days: isNormal ? null : windowLen,
    };
    create.mutate(body, { onSuccess: (run) => onCreated(run.id) });
  };

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Field label="Scenario" htmlFor="gen-scenario">
        <select
          id="gen-scenario"
          value={scenario}
          onChange={(e) => setScenario(e.target.value as Scenario)}
          className="input"
        >
          {SCENARIOS.map((s) => (
            <option key={s} value={s}>
              {SCENARIO[s].plain}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-muted">{SCENARIO[scenario].description}</p>
      </Field>

      <Field label="Run length (days)" htmlFor="gen-duration" error={errors.duration}>
        <input
          id="gen-duration"
          type="number"
          min={1}
          max={120}
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
          aria-describedby={errors.duration ? 'gen-duration-error' : undefined}
          className="input"
        />
      </Field>

      {!isNormal && (
        <>
          <Field label="Stress severity" htmlFor="gen-severity">
            <select
              id="gen-severity"
              value={severity}
              onChange={(e) => setSeverity(e.target.value as SeverityInput)}
              className="input"
            >
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {SEVERITY_INPUT[s]}
                </option>
              ))}
            </select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Window start day" htmlFor="gen-start" error={errors.startDay}>
              <input
                id="gen-start"
                type="number"
                min={1}
                value={startDay}
                onChange={(e) => setStartDay(Number(e.target.value))}
                aria-describedby={errors.startDay ? 'gen-start-error' : undefined}
                className="input"
              />
            </Field>
            <Field label="Window length (days)" htmlFor="gen-window" error={errors.windowLen}>
              <input
                id="gen-window"
                type="number"
                min={1}
                value={windowLen}
                onChange={(e) => setWindowLen(Number(e.target.value))}
                aria-describedby={errors.windowLen ? 'gen-window-error' : undefined}
                className="input"
              />
            </Field>
          </div>
        </>
      )}

      <Field label="Random seed" htmlFor="gen-seed">
        <input
          id="gen-seed"
          type="number"
          value={seed}
          onChange={(e) => setSeed(Number(e.target.value))}
          className="input"
        />
      </Field>

      {create.isError ? <ErrorState error={create.error} /> : null}

      <div className="flex items-center justify-end gap-3 pt-2">
        <Button type="submit" variant="primary" disabled={!valid || create.isPending}>
          {create.isPending ? 'Generating…' : 'Generate run'}
        </Button>
      </div>
      <p className="text-xs text-muted">
        Generating a run also runs the state-analysis, problem-assessment and decision phases for
        every day before it returns.
      </p>
    </form>
  );
}

function Field({
  label,
  htmlFor,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block font-sans text-sm font-medium text-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${htmlFor}-error`} role="alert" className="mt-1 text-xs text-sev-high">
          {error}
        </p>
      ) : null}
    </div>
  );
}
