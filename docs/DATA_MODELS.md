# KAVACH — Data Models

**The frontend must never connect to `backend/kavach.db` directly.** This document exists so a frontend developer understands what backs each API response — access everything through the REST API in `docs/API_CONTRACT.md`.

All 14 tables below are verified present via `sqlite_master` against the live database, and match their SQLAlchemy model 1:1 (no drift found).

---

### `simulation_runs` (1,087 rows) — `app/models/simulation_run.py`
Immutable once created ("regenerate" = a new row, never a mutation). Fields: `id`, `crop`, `duration_days`, `scenario` (`normal|heatwave|water_shortage|excess_irrigation|high_humidity`), `severity` (`mild|moderate|severe`, nullable), `seed`, `scenario_start_day`/`scenario_duration_days` (nullable), `created_at`.
**Frontend access:** via `GET /api/simulator/runs` / `/runs/{id}`.

### `sensor_observations` (114,268 rows) — `app/models/sensor_observation.py`
One row per (run, day, hour∈{0,6,12,18}): `temperature_c`, `humidity_pct`, `soil_moisture_pct`, `daily_dli_mol_m2_day`, `soil_n_mg_kg`, `soil_p_mg_kg`, `soil_k_mg_kg`. Raw simulated sensor data.
**Frontend access:** via `GET /api/simulator/runs/{id}/observations` — generally prefer Phase 3's analyzed output for display; raw observations are for a "sensor detail" view only, if built at all.

### `simulation_internal_state` (114,268 rows) — debug/traceability only, **no API exposure**. Not frontend-relevant.

### `state_analysis_history` (28,151 rows) — Phase 3, `app/models/state_analysis_history.py`
One row per (run, day): `crop`, plus JSON blobs (`parameters_json`, `crop_stages_json`, `agronomic_context_json`, `data_quality_notes_json`) that are exactly what `GET /api/analysis/tomato/runs/{id}` returns, deserialized. **Frontend access:** via that API only — the JSON columns are an internal storage detail, not a contract.

### `problem_assessment_history` (28,305 rows) — Phase 4, `app/models/problem_assessment_history.py`
One row per (run, day): `crop`, `problems_json` (10-category list, same shape as `GET /api/assessment/...`'s `problems`), `computed_at`.

### `decision_history` (19,600 rows) — Phase 5, `app/models/decision_history.py`
One row per (run, day): `crop`, `decisions_json` (10-category list, same shape as `GET /api/decision/...`'s `decisions`), `computed_at`.

### `agronomic_parameters` (58 rows) — Phase 1/5/6, `app/models/agronomic_parameter.py`
General agricultural knowledge AND KAVACH's own project-defined optimization constants, distinguished by `status`. Never farm-specific. **Frontend access:** via `GET /api/agronomics/tomato/parameters` for the knowledge-base view; Phase 6's `project_defined` rows (baseline irrigation, adjustment percentages, efficiency defaults) are internal configuration the frontend does not need to query directly — they surface already-applied in the optimization response's `*_provenance` fields.

### `farm_configurations` (25 rows) — Phase 6, `app/models/farm_configuration.py`
One row per `simulation_run_id` (unique, upsertable — the only table in this project that is *not* append-only, since it's corrective farmer input, not a measurement). Fields: `field_area`, `field_area_unit` (required), `plant_population`, `plant_spacing_m`, `row_spacing_m`, `cultivar`, `irrigation_system_type`, `irrigation_efficiency_pct`, `available_water_l_per_day`, `pump_capacity_l_per_hour`, `pump_power_kw`, `water_cost_per_liter`, `fertilizer_cost_per_kg_{n,p2o5,k2o}` (all optional), `created_at`, `updated_at`.
**Frontend access:** read via the `farm_configuration` block embedded in `GET /api/optimization/...`; write via `POST /api/optimization/tomato/runs/{id}/farm-config`.

### `optimization_history` (8,052 rows) — Phase 6, `app/models/optimization_history.py`
One row per (run, day): `crop`, `optimization_json` (same shape as `GET /api/optimization/...`'s full response body), `computed_at`.

### Phase 0/1 reference tables (`tomato_reference_profile` 120 rows, `data_source` 1 row, `agronomic_sources` 11 rows, `crop_stages` 9 rows, `stress_conditions` 5 rows)
Static/near-static agricultural reference data. **Frontend access:** via `/api/reference/tomato*` and `/api/agronomics/tomato/*` — mainly useful for a "knowledge base" or "sources/provenance" view, not the primary demo flow.

---

## What the frontend must NOT do

- Open or query `backend/kavach.db` directly, from any language/runtime.
- Assume a JSON blob column's internal shape is a stable contract — always go through the documented API response shape, even though today they happen to match.
- Compute plant population, water quantities, savings, or severity itself — every one of these is backend-computed and exposed through an API field.
