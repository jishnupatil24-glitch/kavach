import { useNavigate } from 'react-router-dom';
import { useRunContext } from '@/context/RunContext';
import { useOptimization } from '@/api/hooks/optimization';
import { useQueryClient } from '@tanstack/react-query';
import { clearFarmConfig, OPTIMIZATION_IS_MOCKED } from '@/api/endpoints/optimization';
import { PageHeader } from '@/components/primitives/PageHeader';
import { Button } from '@/components/primitives/Button';
import { SkeletonCard, ErrorState } from '@/components/primitives/states';
import { PrototypeBanner } from '@/components/disclaimers/PrototypeBanner';
import { SampleDataTag } from '@/components/disclaimers/SampleDataTag';
import { FarmConfigForm } from './FarmConfigForm';

export function FarmSetupPage() {
  const { runId, day } = useRunContext();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const optimization = useOptimization(runId, day);
  const cfg = optimization.data?.farm_configuration;

  const backToPlan = () => navigate(`/runs/${runId}/optimization?day=${day}`);

  return (
    <>
      <PageHeader
        eyebrow="4 · Farm Setup"
        title="Configure the farm"
        lead="These inputs turn per-plant figures into whole-field totals, feasibility checks and cost. Only field area and its unit are required."
        actions={<SampleDataTag />}
      />

      <PrototypeBanner />

      {optimization.isLoading ? (
        <SkeletonCard lines={6} />
      ) : optimization.isError ? (
        <ErrorState error={optimization.error} onRetry={() => optimization.refetch()} />
      ) : (
        <div className="card p-6">
          <FarmConfigForm runId={runId} current={cfg} onSaved={backToPlan} />
          {OPTIMIZATION_IS_MOCKED ? (
            <div className="mt-6 border-t border-hairline pt-4">
              <p className="mb-2 text-xs text-muted">
                Prototype affordance: clear the in-memory configuration to see the “not set” and
                UNKNOWN-population states.
              </p>
              <Button
                size="sm"
                variant="danger"
                onClick={() => {
                  clearFarmConfig(runId);
                  qc.invalidateQueries({ queryKey: ['optimization', runId] });
                  optimization.refetch();
                }}
              >
                Clear configuration (prototype)
              </Button>
            </div>
          ) : null}
        </div>
      )}
    </>
  );
}
