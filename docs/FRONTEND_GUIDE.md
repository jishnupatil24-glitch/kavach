# KAVACH — Frontend Guide

## What the frontend is

A presentation/application layer over the 17 implemented REST APIs in `docs/API_CONTRACT.md`. It never computes agronomic, evidentiary, decision, or optimization results itself — the backend is the source of computed truth.

## Product concepts to build (not backend phase names)

Build a coherent KAVACH product. The backend is organized into 6 numbered phases; the UI should not be.

| Build this | Not this |
|---|---|
| Dashboard / Farm overview | "Phase 3 Page" |
| Current Problems | "Phase 4 Page" |
| Recommendations | "Phase 5 Page" |
| Optimized Plan / Resource Savings | "Phase 6 Output Page" |
| Farm Configuration | "Farm Config CRUD" |
| Run / Simulation selector | "Simulation Runs Admin" |
| Decision detail | "Decision Record Viewer" |
| History / trend view | "State Analysis History" |

Suggested concepts and their backing API:

- **Run selector** — `GET /api/simulator/runs`, `POST /api/simulator/runs` (if the frontend lets a user generate a new demo run)
- **Dashboard / current state** — `GET /api/analysis/tomato/runs/{id}?day=`
- **Current Problems** — `GET /api/assessment/tomato/runs/{id}?day=`
- **Recommendations** — `GET /api/decision/tomato/runs/{id}?day=`
- **Optimized Plan / Savings** — `GET /api/optimization/tomato/runs/{id}?day=`
- **Farm Configuration** — `POST /api/optimization/tomato/runs/{id}/farm-config` (write), read via the `farm_configuration` block in the optimization response
- **Knowledge base / sources** (secondary) — `/api/agronomics/tomato/*`, `/api/reference/tomato*`

## Frontend responsibilities

**Should:**
- Call the documented APIs and render their responses.
- Display provenance (`SOURCED`/`PROJECT_DEFINED`/`MODELED`) visibly wherever a number is shown — this project's own backend treats hiding this distinction as a correctness bug, not a style choice.
- Display warnings/limitations arrays verbatim (or a clearly-linked "why" affordance) rather than dropping them.
- Let the user set/update farm configuration.
- Display optimization results, including the honest `UNAVAILABLE`/`null` cases.
- Display history/trend views where useful.
- Handle loading, error, and empty states explicitly (see `docs/DEMO_FLOW.md` / error-states section below).
- Treat `null`, `"UNKNOWN"`, `"UNAVAILABLE"`, and `"NOT_EVALUATED"` as distinct, meaningful states — never coerce any of them to `0`, `false`, or an empty display that reads as "everything is fine."

**Must NOT:**
- Implement any agronomic formula, Phase 4 evidence-gate logic, Phase 5 eligibility/priority logic, or Phase 6 optimization math itself. If the backend doesn't compute something, the frontend does not either — raise it as a backend gap instead.
- Calculate water savings, cost, or plant population independently when the backend already provides (or explicitly withholds) it.
- Connect to `backend/kavach.db` directly (see `docs/DATA_MODELS.md`).
- Modify backend Python code to make a UI feature work — coordinate with the backend developer and document the required API change instead (see Git/collaboration rules below).

## Mocking strategy (Phase 6 final testing is pending — don't let that block frontend work)

Structure the integration as:

```
MOCK DATA  ──┐
             ├──>  API ADAPTER  ──>  UI COMPONENTS
REAL API   ──┘
```

- Build one adapter module per resource (`getOptimization(runId, day)`, `getDecision(runId, day)`, etc.) that returns data shaped **exactly** like `docs/api-examples/*.json` / `docs/API_CONTRACT.md`.
- While Phase 6 is unverified, point the optimization adapter at a local mock JSON file (copy `docs/api-examples/optimization-run-example.json`, which is a real captured response, not fabricated).
- Switching the adapter's implementation from "read local JSON" to "fetch from the real API" should require zero changes to any UI component, because both sides speak the same shape.
- Do **not** invent mock fields that don't appear in `docs/API_CONTRACT.md` — a mock with extra/different fields will silently diverge from the real contract.

## Provenance / display rules

Every optimization number carries one of three tags — surface this, don't hide it:

- **`SOURCED`** — a real external agronomic fact (e.g. ICAR N/P/K demand). Highest confidence.
- **`PROJECT_DEFINED`** — a KAVACH hackathon-prototype assumption (e.g. baseline irrigation L/plant/day, adjustment percentages). Explicitly **not** scientifically validated — the backend's own limitation strings say this; don't strip that caveat out in the UI copy.
- **`MODELED`** — a value computed by combining the above (e.g. the optimized quantity, expected direction). Not measured, not sourced — a deterministic calculation.

Suggested treatment: a small badge/tooltip next to each numeric value showing its tag, and a visible "Prototype optimization model — not a scientifically validated agronomic prescription" banner wherever Phase 6 numbers are shown (this is literally in every optimization response's `limitations` array — display it, don't just log it).

## Error / empty states the frontend must handle

| Situation | Backend signal | Frontend should show |
|---|---|---|
| No problems detected that day | All 10 `problems[].status` are `no_evidence`/`insufficient_data` | "No problems detected" — not a blank/error screen |
| No recommendation | All 10 `decisions[].outcome` are not `ACTION_RECOMMENDED` | "No action recommended" |
| No optimization for the day | `water_optimizations`, `nutrient_optimizations`, `unsupported` all empty | "Nothing to optimize today" |
| Farm configuration missing | `farm_configuration.exists == false` | Prompt to configure the farm; do not silently assume a default |
| Plant population unknown | `plant_population.source == "UNKNOWN"`, `plants == null` | "Unknown — configure plant spacing or population" — never render `0` plants |
| Water/pump capacity not configured | `feasibility[].status == "NOT_EVALUATED"` | "Not evaluated" — visually distinct from PASS (green) and FAIL (red); never render as PASS |
| Cost not configured | `cost.status == "UNAVAILABLE"` | "Cost unavailable — configure a cost rate" — never render `0`/`$0.00` |
| API error (4xx/5xx) | non-2xx HTTP status | A real error state, with the `detail` message from the JSON body where present |
| Invalid run ID | `404` | "Run not found" |
| Invalid day | `422` | "Day out of range for this run" |
| A feature with no backend endpoint yet | n/a | Do not build it against a guessed shape — see `docs/API_CONTRACT.md`'s PLANNED section |

**Never display `0` when the backend means `UNKNOWN`/`UNAVAILABLE`/`NOT_EVALUATED`.** These are `null` in JSON specifically so this distinction survives — check for `null` before formatting any number.

## Git / collaboration rules

- **Backend developer owns:** `backend/app/**`, `backend/tests/**`, database/migrations/seed scripts.
- **Frontend developer owns:** a new `frontend/` directory (components, styles, state management, API adapters).
- **Shared:** `docs/**`, this file, the API contract.
- The frontend developer must not modify backend implementation merely to make a UI feature work. If an API is insufficient, **document the required change** (e.g. a note in `docs/API_CONTRACT.md`'s PLANNED section or a new issue) and coordinate with the backend developer — do not invent undocumented backend behavior inside the frontend.
