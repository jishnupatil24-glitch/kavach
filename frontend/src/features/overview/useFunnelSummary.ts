import { useMemo } from 'react';
import { useAnalysis, useAssessment, useDecision } from '@/api/hooks/pipeline';
import { useOptimization } from '@/api/hooks/optimization';
import type { Severity } from '@/api/types';
import { CATEGORY, TREND_DIRECTION } from '@/lib/plain-language';
import { variableByField } from '@/lib/variables';

const SEV_RANK: Record<Severity, number> = {
  insufficient_data: 0,
  LOW: 1,
  MODERATE: 2,
  HIGH: 3,
  CRITICAL: 4,
};

export interface FunnelCount {
  value: number | null;
  hint: string;
}

export interface FunnelSummary {
  isLoading: boolean;
  counts: Record<string, FunnelCount | null>;
  state: { moving: number | null; total: number; leadVariable: string | null };
  problems: { count: number | null; topSeverity: Severity | null; topCategory: string | null };
  recommendations: { count: number | null; topActionLabel: string | null };
  optimization: {
    quantified: number | null;
    headlineSavingPct: number | null;
    anyUnsupported: boolean;
  };
  changeNote: string | null;
}

export function useFunnelSummary(runId: number | null, day: number | null): FunnelSummary {
  const analysis = useAnalysis({ runId, day });
  const assessment = useAssessment({ runId, day });
  const decision = useDecision({ runId, day });
  const optimization = useOptimization(runId, day);

  return useMemo<FunnelSummary>(() => {
    const params = analysis.data?.parameters ?? [];
    const moving = params.filter(
      (p) => p.trend.direction === 'RISING' || p.trend.direction === 'FALLING',
    );
    const lead = [...moving].sort((a, b) => b.persistence.days - a.persistence.days)[0];
    const leadVariable = lead
      ? (variableByField(lead.current.field)?.plain ?? lead.current.parameter)
      : null;

    const flagged = (assessment.data?.problems ?? []).filter(
      (p) => p.status === 'weak_evidence' || p.status === 'corroborated_evidence',
    );
    const topProblem = [...flagged].sort(
      (a, b) => SEV_RANK[b.severity] - SEV_RANK[a.severity],
    )[0];

    const actions = (decision.data?.decisions ?? []).filter(
      (d) => d.outcome === 'ACTION_RECOMMENDED',
    );
    const topAction =
      actions.find((a) => a.priority === 1) ??
      [...actions].sort((a, b) => (a.priority ?? 99) - (b.priority ?? 99))[0];

    const opt = optimization.data;
    const quantified =
      opt != null
        ? [...opt.water_optimizations, ...opt.nutrient_optimizations].filter(
            (o) =>
              ('optimized_l_per_plant_day' in o
                ? o.optimized_l_per_plant_day
                : o.optimized_g_per_plant_day) != null,
          ).length
        : null;
    const headlineSavingPct = opt?.water_optimizations[0]?.water_saving_percentage ?? null;

    const changeNote = lead
      ? `${leadVariable} has been ${TREND_DIRECTION[lead.trend.direction].plain.toLowerCase()} for ${lead.persistence.days} ${lead.persistence.days === 1 ? 'day' : 'days'}.`
      : null;

    return {
      isLoading:
        analysis.isLoading || assessment.isLoading || decision.isLoading || optimization.isLoading,
      counts: {
        overview: null,
        state: analysis.data
          ? { value: moving.length, hint: `${moving.length} of ${params.length} variables trending` }
          : null,
        problems: assessment.data
          ? { value: flagged.length, hint: `${flagged.length} problem(s) with real evidence` }
          : null,
        recommendations: decision.data
          ? { value: actions.length, hint: `${actions.length} action(s) recommended` }
          : null,
        optimization:
          quantified != null
            ? { value: quantified, hint: `${quantified} quantified optimization(s) — prototype` }
            : null,
      },
      state: {
        moving: analysis.data ? moving.length : null,
        total: params.length,
        leadVariable,
      },
      problems: {
        count: assessment.data ? flagged.length : null,
        topSeverity: topProblem?.severity ?? null,
        topCategory: topProblem ? (CATEGORY[topProblem.category]?.plain ?? topProblem.category) : null,
      },
      recommendations: {
        count: decision.data ? actions.length : null,
        topActionLabel: topAction?.action_label ?? null,
      },
      optimization: {
        quantified,
        headlineSavingPct,
        anyUnsupported: (opt?.unsupported.length ?? 0) > 0,
      },
      changeNote,
    };
  }, [
    analysis.data,
    analysis.isLoading,
    assessment.data,
    assessment.isLoading,
    decision.data,
    decision.isLoading,
    optimization.data,
    optimization.isLoading,
  ]);
}
