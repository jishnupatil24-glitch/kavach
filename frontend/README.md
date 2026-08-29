# KAVACH — Frontend

A presentation layer over the KAVACH FastAPI backend. "A calm field instrument
that tells one honest story." The decision funnel is the product:

**Farm State → Problems → Recommendations → Optimized Plan**

## Stack

React 18 · TypeScript · Vite · Tailwind · Radix primitives · TanStack Query ·
React Router v6 · Recharts · Lucide · Vitest + Testing Library.

## Run it

```bash
cd frontend
npm install
cp .env.example .env      # edit if the backend is not on 127.0.0.1:8000
npm run dev               # http://localhost:5173
```

The dev server proxies `/api` and `/health` to `VITE_DEV_PROXY_TARGET`
(default `http://127.0.0.1:8000`), so the backend's missing CORS middleware is a
non-issue in development. For a deployed build set `VITE_API_BASE_URL` to the
backend origin instead.

**There are no runs in a fresh backend database.** Open the app, then
"Generate a run" — it creates a virtual season and runs the analysis /
assessment / decision phases before returning.

## Verify

```bash
npm run verify   # typecheck + lint + tests + production build
```

## API integration

| Area | Endpoint | Source |
|---|---|---|
| Run switcher / generate | `GET/POST /api/simulator/runs`, `GET /api/simulator/runs/{id}` | real |
| Farm State + charts | `GET /api/analysis/tomato/runs/{id}`, `GET /api/simulator/runs/{id}/observations`, `GET /api/reference/tomato` | real |
| Problems + reasoning | `GET /api/assessment/tomato/runs/{id}` | real |
| Recommendations + reasoning | `GET /api/decision/tomato/runs/{id}` | real |
| Knowledge base | `GET /api/agronomics/tomato/*` | real |
| **Optimized Plan / Farm Setup** | `GET /api/optimization/...`, `POST .../farm-config` | **mock adapter** |

Phase 6 (optimization + farm-config) has no backend route yet
(`docs/API_CONTRACT.md` §7 describes the contract; `backend/app/main.py` does not
mount it). Until it ships, `src/api/mock/optimizationAdapter.ts` serves the two
contract-shaped fixtures captured from the docs. Flip `VITE_MOCK_OPTIMIZATION` to
`false` when the route exists — no component changes needed
(`src/api/endpoints/optimization.ts` is the only switch).

## Architecture

```
components → api/hooks → api/endpoints → api/client → real backend
                        ↘ optimizationAdapter → fixtures   (Phase 6 only)
```

- `src/api/types.ts` mirrors `docs/API_CONTRACT.md` 1:1 — nullable fields are
  `T | null`, enums are string-literal unions, no invented fields.
- `runId` and `day` live in the URL (`/runs/:id/state?day=7`).
- `src/lib/plain-language.ts` is the single enum → plain-wording map.
- `design-system/kavach/MASTER.md` is the implemented design system.

## Not touched

`backend/**`, `data/**`, database files, seed scripts.
