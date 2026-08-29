/** Centralised React Query keys. runId + day are always part of the key. */
export const qk = {
  health: ['health'] as const,
  runs: ['runs'] as const,
  run: (runId: number) => ['run', runId] as const,
  observations: (runId: number, day?: number | null) => ['observations', runId, day ?? null] as const,
  analysis: (runId: number, day: number | null) => ['analysis', runId, day] as const,
  assessment: (runId: number, day: number | null) => ['assessment', runId, day] as const,
  decision: (runId: number, day: number | null) => ['decision', runId, day] as const,
  optimization: (runId: number, day: number | null) => ['optimization', runId, day] as const,
  reference: ['reference'] as const,
  agronomicParameters: (status?: string, domain?: string) =>
    ['agronomics', 'parameters', status ?? null, domain ?? null] as const,
  cropStages: ['agronomics', 'stages'] as const,
  agronomicSources: ['agronomics', 'sources'] as const,
};
