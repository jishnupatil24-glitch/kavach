/**
 * Thin fetch wrapper for the KAVACH backend.
 *
 * Base URL: VITE_API_BASE_URL if set, otherwise same-origin (the Vite dev
 * proxy forwards /api and /health to the FastAPI backend).
 *
 * Error normalisation: FastAPI returns either `{ detail: string }` or, for 422,
 * `{ detail: [{ loc, msg, type }, ...] }`. Both collapse into ApiError.detail.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  readonly httpStatus: number;
  readonly detail: string;
  readonly raw: unknown;

  constructor(httpStatus: number, detail: string, raw: unknown) {
    super(detail || `HTTP ${httpStatus}`);
    this.name = 'ApiError';
    this.httpStatus = httpStatus;
    this.detail = detail;
    this.raw = raw;
  }
}

interface PydanticIssue {
  loc?: (string | number)[];
  msg?: string;
  type?: string;
}

function extractDetail(body: unknown, status: number): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const d = (body as { detail: unknown }).detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      return (d as PydanticIssue[])
        .map((issue) => {
          const path = (issue.loc ?? []).filter((p) => p !== 'body').join('.');
          return path ? `${path}: ${issue.msg ?? 'invalid'}` : (issue.msg ?? 'invalid');
        })
        .join('; ');
    }
  }
  return `Request failed (HTTP ${status}).`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    });
  } catch (e) {
    throw new ApiError(0, 'Cannot reach the KAVACH backend. Is it running?', e);
  }

  const text = await res.text();
  const body = text ? safeJson(text) : null;

  if (!res.ok) {
    throw new ApiError(res.status, extractDetail(body, res.status), body);
  }
  return body as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
};

export async function checkHealth(): Promise<boolean> {
  try {
    const r = await api.get<{ status: string }>('/health');
    return r.status === 'ok';
  } catch {
    return false;
  }
}
