# KAVACH — Backend Status Board

Verified against the repository and `backend/kavach.db` (via `sqlite_master`) directly. Not transcribed from an old plan.

---

## Phase 1 — Agronomic Knowledge Base

- **Status:** COMPLETE
- **Purpose:** General/stage-specific agricultural facts with explicit provenance (sourced/assumption/derived/context_dependent/project_defined), separate from the day-by-day ICAR reference profile.
- **Important modules:** `app/services/seed_agronomics.py`
- **Models:** `app/models/agronomic_parameter.py`, `agronomic_source.py`, `crop_stage.py`, `stress_condition.py`, `agronomic_status.py`
- **API:** `GET /api/agronomics/tomato/sources`, `/stages`, `/stages/{stage_id}`, `/parameters` (filters `?status=`, `?domain=`), `/parameters/{parameter_name}`, `/stress-conditions`
- **CLI:** none dedicated (knowledge-base browsing only via API)
- **Database:** `agronomic_sources` (11 rows), `crop_stages` (9 rows), `agronomic_parameters` (58 rows: 40 Phase-1 + 2 Phase-5 project_defined + 16 Phase-6 project_defined), `stress_conditions` (5 rows, all thresholds NULL — unused placeholder, not wired to any detection logic)

## Phase 2 — Simulation

- **Status:** COMPLETE
- **Purpose:** Generates realistic 6-hour-resolution virtual sensor observations for a configurable scenario. No diagnosis/recommendation logic.
- **Important modules:** `app/services/simulator/{constants,rng,baseline,causal_model,calibration,scenarios,config,generator,run_service}.py`
- **Models:** `app/models/simulation_run.py`, `sensor_observation.py`, `simulation_internal_state.py`
- **API:** `POST /api/simulator/runs`, `GET /api/simulator/runs`, `GET /api/simulator/runs/{run_id}`, `GET /api/simulator/runs/{run_id}/observations`
- **CLI:** `python -m app.simulator_cli`
- **Database:** `simulation_runs` (1,087 rows), `sensor_observations` (114,268 rows), `simulation_internal_state` (114,268 rows, debug-only, no API exposure)

## Phase 3 — State Analysis

- **Status:** COMPLETE
- **Purpose:** Per sensor variable, computes current value, OLS trend/rate, trend persistence, ICAR reference deviation, crop-stage context.
- **Important modules:** `app/services/state_analysis/{parameters,current_state,trend,persistence,icar_deviation,crop_stage_context,service,history}.py`
- **Models:** `app/models/state_analysis_history.py`
- **API:** `GET /api/analysis/tomato/runs/{run_id}` (on-demand compute, `?day=` optional)
- **CLI:** `python -m app.state_analysis_cli --run-id N [--day D]` (read-only, reads persisted history)
- **Database:** `state_analysis_history` (28,151 rows, one per run-day)

## Phase 4 — Problem Assessment

- **Status:** COMPLETE
- **Purpose:** Evaluates Phase 3 output against 10 fixed problem categories (`water_depletion`, `excessive_moisture`, `heat_related`, `temperature_deficit`, `humidity_low`, `humidity_high`, `nitrogen_related`, `phosphorus_related`, `potassium_related`, `light_deficit`), producing evidence status, severity, and abnormal duration.
- **Important modules:** `app/services/stress_assessment/{categories,evidence,abnormal_duration,service,history}.py`
- **Models:** `app/models/problem_assessment_history.py`
- **API:** `GET /api/assessment/tomato/runs/{run_id}` (on-demand compute, `?day=` optional)
- **CLI:** `python -m app.stress_assessment_cli --run-id N [--day D]` (read-only)
- **Database:** `problem_assessment_history` (28,305 rows)
- **Note:** humidity_low/humidity_high evidence logic was corrected this session (see `KAVACH_PROJECT_CONTEXT.md` section M) — fix is in place and regression-tested, but the ~19,600 pre-existing `decision_history` rows computed before the fix have **not** been backfilled (deliberately deferred, not an oversight).

## Phase 5 — Decision Engine

- **Status:** COMPLETE
- **Purpose:** Gates Phase 4's evidenced problems (severity floor, Tier-2 duration floor — both project_defined), detects same-sensor-field opposite-direction conflicts, ranks eligible actions, outputs `ACTION_RECOMMENDED` / `MONITOR` / `NO_ACTION` / `INSUFFICIENT_SUPPORT` / `CONFLICT`. Purely qualitative — no quantities, no LLM.
- **Important modules:** `app/services/decision_engine/{config_parameters,seed_parameters,constraint_engine,prioritization,validation,actions,service,history}.py`
- **Models:** `app/models/decision_history.py`
- **API:** `GET /api/decision/tomato/runs/{run_id}` (on-demand compute, `?day=` optional)
- **CLI:** `python -m app.decision_cli --run-id N [--day D]` (read-only)
- **Database:** `decision_history` (19,600 rows)

## Phase 6 — Quantitative Optimization

- **Status:** **IMPLEMENTED — FINAL TESTING PENDING**
- **Purpose:** For `ACTION_RECOMMENDED` water/nutrient categories, computes baseline vs. optimized quantity, per-plant and field-level totals, water/nutrient savings, cost, resource feasibility, and expected direction — every number tagged SOURCED/PROJECT_DEFINED/MODELED.
- **Important modules:** `app/services/optimization/{units,config_parameters,seed_parameters,population,farm_config,water_model,nutrient_model,feasibility,cost,effectiveness,service,history}.py`
- **Models:** `app/models/farm_configuration.py`, `optimization_history.py`
- **API:** `GET /api/optimization/tomato/runs/{run_id}` (on-demand, `?day=`), `POST /api/optimization/tomato/runs/{run_id}/farm-config` (upsert)
- **CLI:** `python -m app.optimization_cli --run-id N [--day D]` (read-only), `python -m app.services.optimization.farm_config --run-id N --field-area ... --field-area-unit ...` (write/setter, separate)
- **Database:** `farm_configurations` (25 rows), `optimization_history` (8,052 rows)
- **Tests:** 59 dedicated tests, all passing; 327/327 in the full suite
- **What "final testing pending" means concretely:** the 327 automated tests pass and Phase 6 has been manually exercised end-to-end against real generated runs (see `docs/DEMO_DATA.md`), but this project's separate final verification pass (the same kind every earlier phase went through before being marked COMPLETE) has not yet happened. Do not present Phase 6 as fully verified to an end user.

## Phase 7 — Recommendation Validation

- **Status:** NOT STARTED
- No design has been proposed or approved. Do not build against assumed Phase 7 behavior.

## Phase 8 — Final Integration / Product Layer

- **Status:** NOT STARTED
- This is the frontend this handoff package exists for.

---

## CURRENT BACKEND DEVELOPMENT

- Phase 6 final testing/verification: **pending**
- Phase 7: **not started**
- Phase 8: **not started** (frontend, this handoff)

## Verified against live database (`sqlite_master`, 14 tables, no drift from code-defined models)

```
tomato_reference_profile        120
data_source                       1
agronomic_sources                11
crop_stages                       9
agronomic_parameters             58
stress_conditions                 5
simulation_runs                1,087
sensor_observations           114,268
simulation_internal_state     114,268
state_analysis_history         28,151
problem_assessment_history     28,305
decision_history                19,600
farm_configurations                25
optimization_history             8,052
```

## Test suite

327/327 passing (`cd backend && python -m pytest tests/ -v`). Breakdown: Phase 0 (16) · Phase 1 (21) · Phase 2 (23+14 CLI) · Phase 3 (40+12 CLI+14 history) · Phase 4 (per-file: `test_stress_assessment.py`, `test_stress_assessment_cli.py`, `test_stress_assessment_history.py`, `test_stress_assessment_severity.py`) · Phase 5 (`test_decision_engine.py`) · Phase 6 (`test_optimization.py` 46, `test_optimization_cli.py` 6, `test_optimization_history.py` 7).
