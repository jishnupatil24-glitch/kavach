# KAVACH — Project Context (Master File)

## FOR A NEW DEVELOPER / CLAUDE CODE — START HERE

Read these files first, in this order:

1. `KAVACH_PROJECT_CONTEXT.md` (this file)
2. `docs/BACKEND_STATUS.md`
3. `docs/ARCHITECTURE.md`
4. `docs/API_CONTRACT.md`
5. `docs/FRONTEND_GUIDE.md`
6. `docs/PHASE_ROADMAP.md`
7. `docs/DEMO_FLOW.md`
8. `docs/DEMO_DATA.md`

Then inspect the actual repository — this document is a snapshot, verified against the code and the live `backend/kavach.db` (via `sqlite_master`) as of the date this file was written, not a plan. If anything here disagrees with the code, **the code is correct and this file is stale.**

### Current phase status (verified against the repository)

| Phase | Status |
|---|---|
| Phase 1 — Agronomic Knowledge Base | **COMPLETE** |
| Phase 2 — Simulation | **COMPLETE** |
| Phase 3 — State Analysis | **COMPLETE** |
| Phase 4 — Problem Assessment | **COMPLETE** |
| Phase 5 — Decision Engine | **COMPLETE** |
| Phase 6 — Quantitative Optimization | **IMPLEMENTED — FINAL TESTING PENDING** |
| Phase 7 — Recommendation Validation | **NOT STARTED** |
| Phase 8 — Final Integration / Product Layer | **NOT STARTED** |

Phase 6 has 327/327 backend tests passing and has been exercised against real generated simulation runs during implementation, but has **not** been through this project's separate final testing/verification workflow. Do not describe Phase 6 as fully verified. Do not describe Phase 7 or Phase 8 as designed — neither has an approved design yet.

---

## A. Project overview

KAVACH is a sustainability-focused agricultural decision-support system for tomato cultivation in a polyhouse (protected-cultivation) environment. It is a hackathon project built in strict, individually-approved phases, each with its own backend module, database table(s), API, and terminal CLI.

## B. What KAVACH is trying to accomplish

Given continuous sensor observations of a polyhouse, KAVACH detects environmental/crop problems, decides whether an intervention is justified, and — as of Phase 6 — proposes a quantitative resource-optimized plan for the interventions it can quantify. The central resource objective is **water**: avoid unnecessary irrigation, avoid overwatering, and never fabricate a value it cannot support with real data.

## C. High-level architecture

```
Simulator (virtual sensors)
      |
Phase 3  State Analysis        (trend / rate / persistence / ICAR deviation, per sensor variable)
      |
Phase 4  Problem Assessment    (evidence-gated stress detection, 10 categories)
      |
Phase 5  Decision Engine       (eligibility, conflict detection, priority, ACTION_RECOMMENDED)
      |
Phase 6  Quantitative Optimization  (baseline vs optimized quantity, savings, cost, feasibility)
      |
Phase 7  Recommendation Validation   -- NOT STARTED
      |
Phase 8  Frontend / product layer    -- NOT STARTED (this handoff's purpose)
```

Each phase persists its own output as its own database table, computed once per `(simulation_run_id, day)`, and consumes only the **stored** output of the phase directly below it — never raw sensor data, never a recomputation of an earlier phase. This is enforced by structural tests in every phase's test file, not just convention.

## D. Complete phase pipeline

- **Phase 1 — Agronomic Knowledge Base**: sourced/assumption/derived/context-dependent/project-defined agricultural facts (Kc values, temperature/humidity bounds, nutrient totals), each with explicit provenance.
- **Phase 2 — Simulation**: generates realistic 6-hour-resolution virtual sensor observations for a configurable scenario (normal/heatwave/water_shortage/excess_irrigation/high_humidity). Does not diagnose or recommend anything.
- **Phase 3 — State Analysis**: per sensor variable, computes current value, OLS trend, trend persistence, ICAR reference deviation, crop-stage context.
- **Phase 4 — Problem Assessment**: evaluates Phase 3's output against 10 fixed problem categories, produces an evidence status (`insufficient_data`/`no_evidence`/`weak_evidence`/`corroborated_evidence`), a severity score, and an abnormal-duration figure.
- **Phase 5 — Decision Engine**: gates Phase 4's evidenced problems against project-defined severity/duration thresholds, detects same-field opposite-direction conflicts, ranks eligible actions by priority, and outputs one of `ACTION_RECOMMENDED` / `MONITOR` / `NO_ACTION` / `INSUFFICIENT_SUPPORT` / `CONFLICT` per category. Purely qualitative — no quantities.
- **Phase 6 — Quantitative Optimization**: for `ACTION_RECOMMENDED` water and nutrient categories, computes a baseline vs. optimized quantity, per-plant and field-level totals, savings/cost/feasibility, all explicitly tagged `SOURCED`/`PROJECT_DEFINED`/`MODELED`. Other categories (heat, cold, humidity, light) remain qualitative — no equipment model exists for them.
- **Phase 7 — NOT STARTED.** No design has been approved. Do not assume any specific approach.
- **Phase 8 — NOT STARTED.** This handoff package exists so a frontend can begin now, in parallel, against the Phase 1-6 APIs that already exist.

## E. Status — see table above (section header). Repeated in `docs/BACKEND_STATUS.md` with per-phase module/API/CLI/DB detail.

## F. Important files per completed phase

See `docs/ARCHITECTURE.md` for the full file tree. Summary:

| Phase | Service package | Model(s) | Route | CLI |
|---|---|---|---|---|
| 1 | `services/seed_agronomics.py` | `agronomic_parameter.py`, `agronomic_source.py`, `crop_stage.py`, `stress_condition.py` | `routes/agronomics.py` | — |
| 2 | `services/simulator/` | `simulation_run.py`, `sensor_observation.py`, `simulation_internal_state.py` | `routes/simulator.py` | `simulator_cli.py` |
| 3 | `services/state_analysis/` | `state_analysis_history.py` | `routes/state_analysis.py` | `state_analysis_cli.py` |
| 4 | `services/stress_assessment/` | `problem_assessment_history.py` | `routes/stress_assessment.py` | `stress_assessment_cli.py` |
| 5 | `services/decision_engine/` | `decision_history.py` | `routes/decision.py` | `decision_cli.py` |
| 6 | `services/optimization/` | `farm_configuration.py`, `optimization_history.py` | `routes/optimization.py` | `optimization_cli.py` |

## G. Important database tables (verified via `sqlite_master` against the live `backend/kavach.db`)

14 tables exist, all code-defined and database-present (no drift found):

`tomato_reference_profile`, `data_source`, `agronomic_sources`, `crop_stages`, `agronomic_parameters`, `stress_conditions` (Phase 0/1) · `simulation_runs`, `sensor_observations`, `simulation_internal_state` (Phase 2) · `state_analysis_history` (Phase 3) · `problem_assessment_history` (Phase 4) · `decision_history` (Phase 5) · `farm_configurations`, `optimization_history` (Phase 6).

Full field-level detail in `docs/DATA_MODELS.md`.

## H. Existing APIs

All under `http://<host>/api/...`, registered in `app/main.py`. Full detail (params, response shapes, examples) in `docs/API_CONTRACT.md`.

```
GET  /api/reference/tomato
GET  /api/reference/tomato/day/{day}
GET  /api/agronomics/tomato/sources
GET  /api/agronomics/tomato/stages
GET  /api/agronomics/tomato/stages/{stage_id}
GET  /api/agronomics/tomato/parameters
GET  /api/agronomics/tomato/parameters/{parameter_name}
GET  /api/agronomics/tomato/stress-conditions
POST /api/simulator/runs
GET  /api/simulator/runs
GET  /api/simulator/runs/{run_id}
GET  /api/simulator/runs/{run_id}/observations
GET  /api/analysis/tomato/runs/{run_id}
GET  /api/assessment/tomato/runs/{run_id}
GET  /api/decision/tomato/runs/{run_id}
GET  /api/optimization/tomato/runs/{run_id}
POST /api/optimization/tomato/runs/{run_id}/farm-config
GET  /health
```

All are **IMPLEMENTED**. No endpoint in this list is planned/mocked at the code level. Phase 6's two endpoints are implemented and passing tests, but carry the same "final testing pending" caveat as the rest of Phase 6.

## I. Existing CLIs

`python -m app.simulator_cli`, `python -m app.state_analysis_cli --run-id N [--day D]`, `python -m app.stress_assessment_cli --run-id N [--day D]`, `python -m app.decision_cli --run-id N [--day D]`, `python -m app.optimization_cli --run-id N [--day D]` (read-only), `python -m app.services.optimization.farm_config --run-id N --field-area ... --field-area-unit ...` (write/setter, separate from the read-only CLI above).

## J. Current Phase 6 capabilities

- Farm configuration: persistent per `simulation_run_id`, upsertable, `field_area`/`field_area_unit`/`crop` required, everything else optional.
- Plant population: `PROVIDED` (explicit) → `ESTIMATED` (from area + spacing) → `UNKNOWN` — never silently assumed.
- Irrigation: quantitative for `water_depletion` (increase) and `excessive_moisture` (decrease) only. Baseline is a **PROJECT_DEFINED** per-Kc-stage L/plant/day figure; only `kc_initial_stage`, `kc_mid_stage`, `kc_late_stage` are covered — **`kc_development_stage` (day 27-62 of a run) has no approved baseline and reports `UNAVAILABLE`, not a guess.**
- Nutrients: quantitative for `nitrogen_related`/`phosphorus_related`/`potassium_related`, baseline is the **SOURCED** ICAR per-plant-per-day demand figure (`tomato_reference_profile`), direction is always `increase` (these categories are deficiency-only by definition, never severity-dependent).
- Heat/cold/humidity/light categories stay qualitative — no resource model exists for them.
- Resource feasibility (`available_water_l_per_day`, `pump_capacity_l_per_hour`) and cost are optional; missing input reports `NOT_EVALUATED`/`UNAVAILABLE`, never `PASS` and never a fabricated number.
- Every numeric output is tagged `SOURCED` / `PROJECT_DEFINED` / `MODELED`.

## K. Known limitations

- `kc_development_stage` (day 27-62) has no approved irrigation baseline — this is where *both* of the project's own canonical test scenarios happen to land, so the "clean" full-number demo needs a run whose action day falls outside that window (see `docs/DEMO_DATA.md`).
- Pump-capacity feasibility compares against a plain 24-hour ceiling (`pump_capacity_l_per_hour × 24`) — no operating-hours-per-day assumption has been approved, so this is a conservative upper bound, not a realistic duty cycle.
- Fertigation coupling (nutrients delivered via irrigation water) is not modeled — water and nutrient optimizations are independent resource pools.
- Heat/cold/humidity/light have no quantitative model — would require equipment-specific parameters (fan/misting/lamp capacity) not currently in scope.
- Only tomato is supported; ICAR reference data covers day 1-120 only.

## L. Known bugs

None currently open. See "M" below for one fixed this session.

## M. Previously fixed bugs

**Humidity evidence bug (Phase 4, fixed this session):** `humidity_low`/`humidity_high` could reach `ACTION_RECOMMENDED` via the generic trend/ICAR-sign proxy even when the sourced humidity boundary (30-50% / 80-100%) was never actually crossed, because Phase 5's Tier-1 categories carry no duration safeguard. Fixed in `app/services/stress_assessment/evidence.py`: these two categories' evidence status is now driven entirely by a sourced-boundary `boundary_ratio` (0 = no evidence, (0,1) = weak, 1 = corroborated), and severity's deviation input for these two categories uses that same ratio instead of an unrelated ICAR deviation. Regression-tested; `heat_related` and all other categories are untouched.

## N. What is currently unverified

Phase 6 has **not** been through this project's separate final testing/verification workflow (distinct from the 327 automated unit/integration tests, which do pass). Treat every Phase 6 number as implementation-verified but not yet product-verified. Do not present Phase 6 output to an end user as final without that workflow completing.

## O. What remains to build

- Phase 6 final testing/verification (backend team).
- Phase 7 (recommendation validation) — no design exists yet.
- Phase 8 (this frontend).
- A decision on `kc_development_stage`'s baseline (currently `UNAVAILABLE` by design — needs a product decision, not a silent fix).

## P. What the frontend developer should work on now

Build the presentation layer against the 17 implemented APIs listed in section H, starting with: run selection → current problems (Phase 4/5) → recommendations (Phase 5) → optimization (Phase 6) → farm configuration. See `docs/FRONTEND_GUIDE.md` and `docs/DEMO_FLOW.md`.

## Q. What the frontend developer should NOT touch

`backend/app/**` (models, schemas, routes, services), `backend/tests/**`, `backend/kavach.db`, any seed/migration script. Never connect to the SQLite file directly — every value the frontend needs is already exposed through an API.

## R. Final intended user journey

Farmer/judge picks a simulation run → sees current problems and their evidence/severity → sees Phase 5's recommended action(s) → for water/nutrient actions, sees Phase 6's optimized quantity, savings, cost, and feasibility, all with visible provenance and limitations → for other actions, sees the qualitative recommendation as-is.

## S. Integration strategy

Frontend calls the REST APIs directly (see `docs/API_CONTRACT.md`); use `docs/api-examples/*.json` for shape while iterating. No mock server is provided by the backend — see `docs/FRONTEND_GUIDE.md`'s mocking-strategy section for how to structure an adapter so switching from local mock JSON to the real API requires no component rewrites.
