# KAVACH

KAVACH is a sustainability-focused agricultural decision-support system for
tomato cultivation in a polyhouse (protected-cultivation) environment. Its
central resource objective is **water**: recommend the minimum irrigation
intervention needed to keep the crop in an acceptable state — including
recommending *no* intervention when none is needed — and never fabricate a
value it cannot support with real data.

Given continuous virtual-sensor observations of a polyhouse, KAVACH detects
environmental/crop problems, decides whether an intervention is justified,
and — for the interventions it can quantify — proposes a resource-optimized
plan with an explicit water-impact figure and visible provenance for every
number.

## The KAVACH pipeline

```
ICAR / reference data            Phase 0  ingested tomato polyhouse reference profile (Day 1–120)
        |
Agronomic knowledge base         Phase 1  sourced / assumption / project-defined agronomic facts
        |
Virtual sensor simulation        Phase 2  causally-consistent 6-hour sensor observations per scenario
        |
State analysis                   Phase 3  per-variable value, OLS trend, persistence, ICAR deviation, crop stage
        |
Stress / problem assessment      Phase 4  evidence-gated stress detection across 10 problem categories
        |
Decision engine                  Phase 5  eligibility gating, conflict detection, priority, ACTION_RECOMMENDED / MONITOR / NO_ACTION
        |
Optimization                     Phase 6  resource-aware quantity: baseline vs optimized, savings, cost, feasibility
        |
Farmer-facing recommendation     water-impact classification + qualitative recommendations, presented by the frontend
```

Each phase persists its own output to its own database table, computed once
per `(simulation_run_id, day)`, and consumes only the **stored** output of
the phase directly below it — never raw sensor data, never a recomputation
of an earlier phase.

### What Phase 6 (optimization) actually provides

- For `ACTION_RECOMMENDED` **water** categories (`water_depletion`,
  `excessive_moisture`) and **nutrient** categories (`nitrogen_related`,
  `phosphorus_related`, `potassium_related`): a baseline quantity vs. an
  optimized quantity, per-plant and field-level totals, and a
  savings / cost / feasibility assessment.
- **Water-impact calculation:** every water optimization carries three
  distinct quantities — theoretical crop requirement (`PROJECT_DEFINED`),
  typical farmer application (`PROJECT_DEFINED`, a prototype assumption),
  and the KAVACH recommendation (`MODELED`) — and the farmer-facing metric
  is *typical application vs. KAVACH recommendation*
  (`water_saved_vs_typical_l_per_day` / `_percentage`). Positive = water
  saved, negative = additional water required; an increase is never
  labelled a saving.
- Every numeric output is tagged `SOURCED` / `PROJECT_DEFINED` / `MODELED`.
- Heat / cold / humidity / light categories stay **qualitative** — no
  equipment model exists for them, so no quantity is invented.

## Phase status

| Phase | Scope | Status |
|---|---|---|
| Phase 0 | ICAR reference data ingestion | **COMPLETE** |
| Phase 1 | Agronomic knowledge base | **COMPLETE** |
| Phase 2 | Virtual sensor simulator | **COMPLETE** |
| Phase 3 | Sensor history / state analysis | **COMPLETE** |
| Phase 4 | Stress / problem assessment | **COMPLETE** |
| Phase 5 | Decision engine | **COMPLETE** |
| Phase 6 | Resource-aware optimization | **IMPLEMENTED / TESTED** |
| Phase 7 | Recommendation validation | **NOT STARTED** |

Phase 6 passes the full automated test suite and has been exercised against
real generated simulation runs, but has not been through the project's
separate final product-verification workflow — treat its numbers as
implementation-verified, not yet product-verified. Phase 7 does not exist;
no design for it has been approved.

`KAVACH_PROJECT_CONTEXT.md` and `docs/BACKEND_STATUS.md` carry the
per-phase module / API / CLI / database detail.

## Repository layout

```
backend/          FastAPI + SQLAlchemy service, one package per phase, plus CLIs and tests
frontend/         React + TypeScript + Vite presentation layer (the decision funnel)
data/seed/        tomato_reference.csv — verified extraction of the ICAR table (DB is seeded from this)
data/sources/     tomato_reference.pdf — original ICAR-derived dataset, kept as-is for provenance
docs/             architecture, API contract, data models, phase roadmap, demo flow/data
```

The SQLite database (`backend/kavach.db`) is **not** committed — it is
rebuilt locally from the seed scripts below.

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- No external services, API keys, or network access required.

---

## Backend setup

All backend commands are run from the `backend/` directory.

```bash
cd backend

# 1. Python environment
python -m venv .venv
.venv/Scripts/activate         # Windows
# source .venv/bin/activate    # macOS / Linux

# 2. Dependencies
pip install -r requirements.txt

# 3. Initialize + seed the database (creates backend/kavach.db).
#    Run all four, in this order. Each is idempotent and safe to re-run.
python -m app.services.seed_database                       # ICAR reference profile  (Phase 0)
python -m app.services.seed_agronomics                     # agronomic knowledge base (Phase 1)
python -m app.services.decision_engine.seed_parameters     # Phase 5 project-defined parameters
python -m app.services.optimization.seed_parameters        # Phase 6 project-defined parameters

# 4. Start the API
uvicorn app.main:app --reload
```

The database schema is created automatically by the seed scripts
(`Base.metadata.create_all`); there is no separate migration step.

Re-deriving the seed CSV from the source PDF is **optional** (the verified
CSV is already committed) — `python -m app.services.extract_reference`
regenerates `data/seed/tomato_reference.csv` from
`data/sources/icar/tomato_reference.pdf`.

The backend has **no CORS middleware** — in development the frontend's Vite
dev server proxies API calls, so this is a non-issue. For a split-origin
deployment you would need to add CORS.

---

## Frontend setup

All frontend commands are run from the `frontend/` directory.

```bash
cd frontend

# 1. Dependencies
npm install

# 2. Environment
cp .env.example .env            # defaults already target a local backend

# 3. Start the dev server
npm run dev                     # http://localhost:5173
```

### Environment configuration

`frontend/.env` (copied from `.env.example`) controls how the frontend
reaches the backend:

| Variable | Default | Meaning |
|---|---|---|
| `VITE_API_BASE_URL` | *(blank)* | Backend origin for a deployed build. Blank = call `/api/*` on the same origin and let the Vite dev proxy forward it. |
| `VITE_DEV_PROXY_TARGET` | `http://127.0.0.1:8000` | Where `npm run dev` proxies `/api` and `/health`. |
| `VITE_MOCK_OPTIMIZATION` | `false` | `false` (or unset) → Phase 6 views call the **real backend**. `true` → opt-in local fixtures, for demoing the UI with the backend offline only. |

**The frontend uses the real backend by default.** Phase 6 optimization
data only comes from local fixtures if `VITE_MOCK_OPTIMIZATION=true` is set
explicitly; when that happens a visible "Sample data — backend not yet
connected" badge appears on the affected views. For the hackathon demo,
leave it `false`.

`frontend/.env` is git-ignored — only `.env.example` is committed, and it
contains no secrets.

---

## Run KAVACH

Two terminals:

**Terminal 1 — backend**

```bash
cd backend
.venv/Scripts/activate         # or: source .venv/bin/activate
uvicorn app.main:app --reload
```

Backend runs at **http://127.0.0.1:8000**.

- Health check: `GET http://127.0.0.1:8000/health` → `{"status": "ok"}`
- Interactive API docs (FastAPI, auto-generated): **http://127.0.0.1:8000/docs**
- Alternative API docs: **http://127.0.0.1:8000/redoc**

**Terminal 2 — frontend**

```bash
cd frontend
npm run dev
```

Frontend runs at **http://localhost:5173** and proxies `/api` + `/health`
to the backend on port 8000.

### Using the app

A fresh database has **no simulation runs**. Open the frontend, use
**"Generate a run"** — it creates a virtual season and runs the analysis /
assessment / decision / optimization phases before returning. Then walk the
funnel: **Farm State → Problems → Recommendations → Optimized Plan → Farm
Setup**.

### Key API endpoints

All under `http://127.0.0.1:8000` (full detail in `docs/API_CONTRACT.md`):

```
GET  /health
GET  /api/reference/tomato                              GET  /api/reference/tomato/day/{day}
GET  /api/agronomics/tomato/sources | stages | parameters | stress-conditions
POST /api/simulator/runs                                GET  /api/simulator/runs | /{run_id} | /{run_id}/observations
GET  /api/analysis/tomato/runs/{run_id}                 (Phase 3)
GET  /api/assessment/tomato/runs/{run_id}               (Phase 4)
GET  /api/decision/tomato/runs/{run_id}                 (Phase 5)
GET  /api/optimization/tomato/runs/{run_id}             (Phase 6)
POST /api/optimization/tomato/runs/{run_id}/farm-config (Phase 6)
```

### Command-line demos (no API server needed)

```bash
cd backend
python -m app.simulator_cli                              # generate a run interactively
python -m app.state_analysis_cli    --run-id N [--day D] # Phase 3
python -m app.stress_assessment_cli --run-id N [--day D] # Phase 4
python -m app.decision_cli          --run-id N [--day D] # Phase 5
python -m app.optimization_cli      --run-id N [--day D] # Phase 6 (read-only)
```

---

## Tests

**Backend**

```bash
cd backend
pytest tests/ -v
```

**Frontend**

```bash
cd frontend
npm run verify        # typecheck + lint + unit tests + production build
```

---

## The reference dataset

`data/sources/icar/tomato_reference.pdf` is the original ICAR-derived tomato
polyhouse dataset (Day 1–120), kept as-is for provenance and traceability.
It is **not** modified during extraction.

**This is a reference profile, not live sensor data.** It describes an
expected/baseline crop trajectory (environmental conditions, target soil NPK
concentrations, and modelled daily nutrient demand) for a tomato polyhouse —
it is not a "ground truth" label, not simulated sensor data, and not a
direct recommendation table.

`data/seed/tomato_reference.csv` is the structured, verified extraction of
that PDF's table, produced by `app.services.extract_reference`. Extraction
performs no estimation, interpolation, correction, or invention of values —
it parses exactly what the PDF table contains and validates structural
expectations (120 rows, days 1–120 with no gaps/duplicates, all values
numeric). The pipeline is:

```
ICAR PDF  ->  extracted/verified CSV  ->  SQLite  ->  API
```

### Columns

| CSV/DB column              | Meaning                              |
|----------------------------|--------------------------------------|
| `day`                      | Day number, 1–120                    |
| `soil_moisture_pct`        | Soil moisture (%)                    |
| `temperature_c`            | Temperature (°C)                     |
| `humidity_pct`             | Humidity (%)                         |
| `dli_mol_m2_day`           | Daily Light Integral (mol/m²/day)    |
| `soil_n_mg_kg`             | Soil nitrogen (mg/kg)                |
| `soil_p_mg_kg`             | Soil phosphorus (mg/kg)              |
| `soil_k_mg_kg`             | Soil potassium (mg/kg)               |
| `n_demand_g_plant_day`     | N demand (g/plant/day)               |
| `p2o5_demand_g_plant_day`  | P₂O₅ demand (g/plant/day)            |
| `k2o_demand_g_plant_day`   | K₂O demand (g/plant/day)             |

Nutrient identity is kept explicit throughout: `soil_p_mg_kg` (elemental P)
is never treated as equal to `p2o5_demand_g_plant_day` (P₂O₅), and likewise
for K vs. K₂O.

## Known limitations

- Only **tomato** is supported; ICAR reference data covers day 1–120 only.
- `kc_development_stage` (roughly day 27–62 of a run) has no approved
  irrigation baseline, so Phase 6 reports `UNAVAILABLE` for it rather than
  guessing — see `docs/DEMO_DATA.md` for choosing a demo run whose action
  day lands outside that window.
- Fertigation coupling (nutrients delivered via irrigation water) is not
  modeled — water and nutrient optimizations are independent.
- Phase 6's pump-capacity feasibility check uses a plain 24-hour ceiling,
  not a realistic duty cycle.
- Phase 7 (recommendation validation) and a full product layer are not
  started.

See `KAVACH_PROJECT_CONTEXT.md` for the complete engineering context.
