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
| **Optimized Plan / Farm Setup** | `GET /api/optimization/...`, `POST .../farm-config` | **real** |

Phase 6 (optimization + farm-config) IS implemented and mounted in
`backend/app/main.py`. `VITE_MOCK_OPTIMIZATION=false` in `.env` (the
`.env.example` default) points every Phase 6 view at the real API.
`src/api/mock/optimizationAdapter.ts` still exists as a dev-only fallback
(set `VITE_MOCK_OPTIMIZATION=true` to force it, e.g. demoing with the
backend offline) — `src/api/endpoints/optimization.ts` is the one switch,
no component changes needed either way. `SampleDataTag` self-hides the
moment the flag is off, so a stray "sample data" badge on screen means the
flag is on, not that the backend is missing.

## Architecture

```
components → api/hooks → api/endpoints → api/client → real backend
                        ↘ optimizationAdapter → fixtures   (dev-only fallback)
```

- `src/api/types.ts` mirrors `docs/API_CONTRACT.md` 1:1 — nullable fields are
  `T | null`, enums are string-literal unions, no invented fields.
- `runId` and `day` live in the URL (`/runs/:id/state?day=7`).
- `src/lib/plain-language.ts` is the single enum → plain-wording map.
- `design-system/kavach/MASTER.md` is the implemented design system.

## Current vs historical (Phase 6 + everywhere `day` applies)

The backend has no separate "latest" concept — a run is a finished virtual
season, and "current" simply means its last day. `RunContext.rawDay` is
`null` when the URL has no `?day=`, in which case `day` falls back to
`durationDays` (the run's last day) — that state is labelled **"Current
plan"**. Any explicit `?day=N` — including typing in the run's own last day
— is labelled **"Historical"**. See `DayScrubber.tsx`. Neither path
recomputes anything: `GET /api/optimization/.../{run_id}?day=` always
computes fresh from Phase 5's *stored* decision for that specific day, so
"current" and "historical" differ only in which day the URL asks for.

## The three water quantities (Optimized Plan)

Every water optimization now carries three distinct numbers — never
conflate them:

1. **Theoretical crop requirement** (`baseline_l_per_plant_day` /
   `baseline_l_per_day`) — the existing Phase 6 baseline. `PROJECT_DEFINED`.
   A modelling input, not what a farmer would apply.
2. **Typical application** (`typical_l_per_plant_day` / `typical_l_per_day`)
   — how much MORE than the theoretical requirement a farmer typically
   applies without decision support (`typical_application_multiplier_pct`,
   currently 40%). `PROJECT_DEFINED` — explicitly a KAVACH prototype
   assumption, not measured/sourced farmer behavior. This is what makes
   KAVACH's value proposition ("precise irrigation avoids over-application")
   visible, and is the **primary** farmer-facing comparison point.
3. **KAVACH recommendation** (`optimized_l_per_plant_day` /
   `optimized_l_per_day`) — the existing Phase 6 optimized quantity.
   `MODELED`.

The **primary** water-impact metric farmers/judges should see is #2 vs #3
(`water_saved_vs_typical_l_per_day` / `_percentage` — see
`src/lib/waterImpact.ts`'s `classifyWaterImpact`, rendered by
`WaterImpactPanel.tsx`), not #1 vs #3. #1 vs #3 (the original
`water_saved_l_per_day`) stays on the card as a secondary "vs theoretical
requirement" reference (`SavingsPanel.tsx`), visually and textually kept
apart from the typical-application story. **Sign convention:** positive =
saved, negative = "additional water required" — never call an increase a
saving, even for `water_depletion` (Phase 5's "increase irrigation" case
can still show a saving vs typical application, if KAVACH's precise
quantity is below what a farmer would typically over-apply).

All arithmetic lives in `backend/app/services/optimization/water_model.py`
(`typical_l_per_plant_day = baseline × (1 + multiplier/100)`, seeded via
`python -m app.services.optimization.seed_parameters`). The frontend never
recomputes it — `classifyWaterImpact` only labels an already-signed number.

## Complete diagnosis + recovery estimate

`CompleteDiagnosisCard.tsx` fuses the matching Phase 5 `DecisionRecord`
(problem, evidence, severity, abnormal duration, recommended action) with
the Phase 6 `WaterOptimization` (typical/theoretical/KAVACH quantities,
water impact, review cycle, expected direction) and a "what happens next"
strip, all sourced from already-fetched API data.

The one exception is the **recovery-window estimate**
(`src/lib/recoveryEstimate.ts`): the backend explicitly does not model
recovery time (`effectiveness.py`'s own docstring: "never a recovery-time
or magnitude claim... the approved Phase 6 design's explicit ban on
both"). `estimateRecoveryWindow()` is a frontend-only, clearly-labelled
prototype heuristic (`review_cycle_days` to `review_cycle_days × severity
multiplier`, confidence always `LOW`) — never persisted, never sent to the
backend, never rendered as a single-day claim. Missing inputs (severity,
review cycle) return `null`, rendered as "Recovery estimate — Unavailable".

## Not touched

`backend/**`, `data/**`, database files, seed scripts.
