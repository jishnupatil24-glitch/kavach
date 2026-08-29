import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './client';

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => (typeof body === 'string' ? body : JSON.stringify(body)),
  } as Response);
}

afterEach(() => vi.unstubAllGlobals());

describe('api client error normalisation', () => {
  it('flattens a FastAPI string detail', async () => {
    vi.stubGlobal('fetch', mockFetch(404, { detail: 'No simulation run found with id 5' }));
    await expect(api.get('/x')).rejects.toMatchObject({
      httpStatus: 404,
      detail: 'No simulation run found with id 5',
    });
  });

  it('flattens a Pydantic 422 detail array', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch(422, {
        detail: [{ loc: ['body', 'severity'], msg: 'field required', type: 'value_error.missing' }],
      }),
    );
    const err: unknown = await api.get('/x').catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    if (!(err instanceof ApiError)) throw err;
    expect(err.httpStatus).toBe(422);
    expect(err.detail).toContain('severity: field required');
  });

  it('reports an unreachable backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('down')));
    await expect(api.get('/x')).rejects.toMatchObject({ httpStatus: 0 });
  });

  it('parses a successful JSON body', async () => {
    vi.stubGlobal('fetch', mockFetch(200, [{ id: 1 }]));
    await expect(api.get('/x')).resolves.toEqual([{ id: 1 }]);
  });
});
