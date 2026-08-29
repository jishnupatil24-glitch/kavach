import type { SimulationRun } from '@/api/types';
import { SCENARIO, SEVERITY_INPUT } from '@/lib/plain-language';

export function runLabel(run: SimulationRun): string {
  const scen = SCENARIO[run.scenario]?.plain ?? run.scenario;
  const sev = run.severity ? ` · ${SEVERITY_INPUT[run.severity] ?? run.severity}` : '';
  return `${scen}${sev}`;
}

export function runSubLabel(run: SimulationRun): string {
  const w =
    run.scenario_start_day != null && run.scenario_duration_days != null
      ? `window day ${run.scenario_start_day}–${run.scenario_start_day + run.scenario_duration_days - 1}`
      : 'no stress window';
  return `#${run.id} · ${run.duration_days}-day run · ${w}`;
}
