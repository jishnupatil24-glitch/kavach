# KAVACH — API Contract

**This is the most important file for the frontend developer.** Every endpoint below is verified directly against the actual route file and Pydantic schema in the repository (file paths given per section). Nothing here is planned or aspirational — a separate "PLANNED / NOT YET IMPLEMENTED" section at the bottom lists everything that does **not** exist yet.

Base URL: whatever host runs `uvicorn app.main:app` (not fixed by the repo — coordinate with backend dev for the actual dev URL/port). All routes are prefixed `/api/...`.

Enum-shaped string fields are marked `enum(...)`. `nullable` means the JSON value can be `null`. All response models use Pydantic's `from_attributes=True`, so the JSON key names below are exact.

---

## 1. Reference (Phase 0) — `app/routes/reference.py`, `app/schemas/tomato_reference.py`

### `GET /api/reference/tomato`
Returns all 120 ICAR reference rows, ordered by day.

**Response:** `200 OK`, `list[TomatoReferenceProfileOut]`
```json
[{
  "day": 1, "soil_moisture_pct": 0.0, "temperature_c": 0.0, "humidity_pct": 0.0,
  "dli_mol_m2_day": 0.0, "soil_n_mg_kg": 0.0, "soil_p_mg_kg": 0.0, "soil_k_mg_kg": 0.0,
  "n_demand_g_plant_day": 0.0, "p2o5_demand_g_plant_day": 0.0, "k2o_demand_g_plant_day": 0.0
}]
```
All fields are non-nullable floats/int.

### `GET /api/reference/tomato/day/{day}`
Path param: `day` (int, 1-120). **404** if out of range. Response: single `TomatoReferenceProfileOut` object (same shape as above).

---

## 2. Agronomics (Phase 1) — `app/routes/agronomics.py`, `app/schemas/agronomics.py`

### `GET /api/agronomics/tomato/sources` → `list[AgronomicSourceOut]`
```json
{"id": 1, "organization_or_author": "string|null", "title": "string|null",
 "publication_year": 2025, "source_type": "string|null", "document_reference": "string|null",
 "description": "string|null", "notes": "string|null"}
```

### `GET /api/agronomics/tomato/stages` → `list[CropStageOut]`
### `GET /api/agronomics/tomato/stages/{stage_id}` → `CropStageOut` (**404** if not found)
```json
{"id": 1, "crop": "tomato", "name": "kc_mid_stage", "start_day": 63, "end_day": 100,
 "description": "string|null", "source_id": 2, "notes": "string|null"}
```
`start_day`/`end_day` are `null` for phenological stages with no day mapping (e.g. `germination`).

### `GET /api/agronomics/tomato/parameters?status=&domain=` → `list[AgronomicParameterOut]`
Query params both optional. `status` is one of `enum(sourced, assumption, missing, source_needed, derived, context_dependent, project_defined)`.
```json
{"id": 1, "crop": "tomato", "domain": "water", "parameter_name": "kc_mid",
 "value_numeric": 1.08, "value_min": null, "value_max": null, "value_text": null,
 "unit": null, "stage_id": 3, "context": "string|null", "status": "sourced",
 "source_id": 2, "notes": "string|null"}
```
Exactly one of `value_numeric` or (`value_min` and `value_max`) is populated; both may be `null` for `derived`/`context_dependent`/`missing`/`source_needed` rows.

### `GET /api/agronomics/tomato/parameters/{parameter_name}` → `list[AgronomicParameterOut]` (**404** if no rows)
### `GET /api/agronomics/tomato/stress-conditions` → `list[StressConditionOut]`
```json
{"id": 1, "crop": "tomato", "stress_type": "string", "affected_parameter": "string",
 "operator": "string", "threshold_value": null, "unit": null, "stage_id": null,
 "severity": null, "status": "missing", "source_id": null, "description": null, "notes": null}
```
Every row currently has `threshold_value: null` and `status: "missing"` — this table is a knowledge-only placeholder, not wired into Phase 4 detection.

---

## 3. Simulator (Phase 2) — `app/routes/simulator.py`, `app/schemas/simulator.py`

### `POST /api/simulator/runs`
**Request body** (`SimulationRunCreate`):
```json
{
  "duration_days": 38,
  "scenario": "excess_irrigation",
  "seed": 123456,
  "severity": "severe",
  "scenario_start_day": 27,
  "scenario_duration_days": 9
}
```
- `scenario`: `enum(normal, heatwave, water_shortage, excess_irrigation, high_humidity)`
- `severity`: `enum(mild, moderate, severe)` — **must be `null` if `scenario` is `"normal"`, required otherwise**
- `scenario_start_day`/`scenario_duration_days`: **must both be `null` if `scenario` is `"normal"`, both required otherwise**
- Validation failures → **422** with a Pydantic validation-error body (not a plain string).

**Response:** `201 Created`, `SimulationRunOut`:
```json
{"id": 584, "crop": "tomato", "duration_days": 48, "scenario": "excess_irrigation",
 "severity": "severe", "seed": 1234, "scenario_start_day": 31, "scenario_duration_days": 16,
 "created_at": "2026-08-26T00:30:38+00:00"}
```
Creating a run **synchronously triggers Phases 3, 4, 5, and 6's own automatic backend processing** for the entire run before this response returns — by the time you get the 201, `state_analysis_history`, `problem_assessment_history`, `decision_history`, and `optimization_history` all already exist for every day of the run.

### `GET /api/simulator/runs` → `list[SimulationRunOut]`
### `GET /api/simulator/runs/{run_id}` → `SimulationRunOut` (**404** if unknown)
### `GET /api/simulator/runs/{run_id}/observations?day=` → `list[SensorObservationOut]`
```json
{"id": 1, "simulation_run_id": 584, "day": 1, "hour": 0, "temperature_c": 0.0,
 "humidity_pct": 0.0, "soil_moisture_pct": 0.0, "daily_dli_mol_m2_day": 0.0,
 "soil_n_mg_kg": 0.0, "soil_p_mg_kg": 0.0, "soil_k_mg_kg": 0.0}
```
`hour` is one of `0, 6, 12, 18`. This is Phase 2's raw generated data — the frontend should generally prefer Phase 3's analyzed output (below) over raw observations for display.

---

## 4. State Analysis (Phase 3) — `app/routes/state_analysis.py`, `app/schemas/state_analysis.py`

### `GET /api/analysis/tomato/runs/{run_id}?day=`
Computed **on demand** (not read from `state_analysis_history`). **404** unknown run, **422** out-of-range day.

**Response:** `StateAnalysisOut`
```json
{
  "run_id": 584, "crop": "tomato", "analysis_day": 37, "duration_days": 48,
  "parameters": [{
    "current": {"parameter": "soil_moisture_pct", "field": "soil_moisture_pct", "value": 61.2, "day": 37, "n_readings": 4, "note": null},
    "trend": {"parameter": "soil_moisture_pct", "direction": "RISING", "rate_per_day": 0.8, "rate_unit": "pp/day", "standard_error_per_day": 0.1, "stable_band": 0.2, "n_observations": 148, "note": null},
    "persistence": {"parameter": "soil_moisture_pct", "direction": "RISING", "days": 9, "note": null},
    "icar": {"parameter": "soil_moisture_pct", "current_value": 61.2, "icar_value": 55.0, "icar_day": 37, "signed_difference": 6.2, "absolute_difference": 6.2, "unit_suffix": " %", "note": null}
  }],
  "crop_stages": [{"stage_id": 2, "name": "kc_development_stage", "start_day": 27, "end_day": 62, "source_id": 2}],
  "agronomic_context": [],
  "data_quality_notes": []
}
```
`trend.direction`: `enum(RISING, FALLING, STABLE, UNDETERMINED)`. `parameters` has one entry per sensor variable (temperature, humidity, soil moisture, DLI, soil N/P/K — 7 total). `crop_stages` can contain more than one entry (e.g. real day-100 overlap between `kc_mid_stage`/`kc_late_stage`) — never assume exactly one.

---

## 5. Stress Assessment (Phase 4) — `app/routes/stress_assessment.py`, `app/schemas/stress_assessment.py`

### `GET /api/assessment/tomato/runs/{run_id}?day=`
Computed **on demand**. **404** unknown run, **422** out-of-range day.

**Response:** `StressAssessmentOut` — `problems` always has **exactly 10 entries** (one per category, regardless of status):
```json
{
  "run_id": 584, "crop": "tomato", "assessment_day": 37,
  "problems": [{
    "category": "excessive_moisture", "label": "Excessive Moisture", "field": "soil_moisture_pct",
    "status": "weak_evidence", "direction": "RISING", "current_value": 61.2,
    "icar_value": 55.0, "icar_deviation": 6.2, "rate_per_day": 0.8, "rate_unit": "pp/day",
    "persistence_days": 9,
    "sourced_corroboration_notes": [], "provenance_notes": [],
    "raw_range": {"min_value": 60.1, "max_value": 62.0, "n_readings": 4, "label": "Descriptive raw sensor range -- not used as an independent stress signal."},
    "severity": "MODERATE",
    "severity_factors": {"deviation_ratio": 0.11, "deviation_score": 1, "intensity_ratio": 2.6, "intensity_score": 1, "duration_fraction": 0.24, "duration_score": 0, "total_score": 2},
    "severity_disclaimer": "Severity is a deterministic observational/analytical severity score derived from Phase 3 signals. It is not itself an agronomic diagnosis and its band boundaries are not sourced agronomic thresholds.",
    "abnormal_state_duration": {"category": "excessive_moisture", "tier": "icar_sign_trend_proxy", "days": 9, "provenance_note": "string"}
  }],
  "crop_stages": [{"stage_id": 2, "name": "kc_development_stage", "start_day": 27, "end_day": 62, "source_id": 2}]
}
```
`status`: `enum(insufficient_data, no_evidence, weak_evidence, corroborated_evidence)`. `severity`: `enum(insufficient_data, LOW, MODERATE, HIGH, CRITICAL)` — **independent of `status`**; a `no_evidence` problem can still show a non-trivial `severity` value, and the frontend must not conflate the two. `abnormal_state_duration.tier`: `enum(sourced_threshold, icar_sign_trend_proxy)`. `severity_factors` is `null` when `severity` is `"insufficient_data"`.

The 10 fixed `category` values: `water_depletion`, `excessive_moisture`, `heat_related`, `temperature_deficit`, `humidity_low`, `humidity_high`, `nitrogen_related`, `phosphorus_related`, `potassium_related`, `light_deficit`.

---

## 6. Decision Engine (Phase 5) — `app/routes/decision.py`, `app/schemas/decision.py`

### `GET /api/decision/tomato/runs/{run_id}?day=`
Computed **on demand**. **404** unknown run, **422** out-of-range day.

**Response:** `DecisionAssessmentOut` — `decisions` always has exactly 10 entries:
```json
{
  "run_id": 584, "crop": "tomato", "assessment_day": 37,
  "decisions": [{
    "category": "excessive_moisture", "label": "Excessive Moisture",
    "status": "weak_evidence", "severity": "MODERATE",
    "abnormal_duration_days": 9, "abnormal_duration_tier": "icar_sign_trend_proxy",
    "eligibility_checks": [
      {"name": "evidence_status", "passed": true, "detail": "status=weak_evidence"},
      {"name": "severity_floor", "passed": true, "detail": "severity=MODERATE vs configured floor=MODERATE"},
      {"name": "duration_floor", "passed": true, "detail": "abnormal_state_duration.days=9 vs configured floor=5"}
    ],
    "conflict_with": null,
    "outcome": "ACTION_RECOMMENDED",
    "action_label": "Reduce irrigation", "action_type": "QUALITATIVE",
    "action_basis": "string", "decision_provenance": "PROJECT_DEFINED",
    "quantitative_basis": null,
    "limitations": ["No quantitative agronomic/operational parameter ... recommendation is qualitative only, never a fabricated quantity."],
    "priority": 1, "priority_reason": "string"
  }]
}
```
`outcome`: `enum(ACTION_RECOMMENDED, MONITOR, NO_ACTION, INSUFFICIENT_SUPPORT, CONFLICT)`. `eligibility_checks[].passed`: `true` (passed) | `false` (evaluated and failed) | `null` (not evaluable — **the frontend must render this as "not evaluable", never coerce to false or true**). `quantitative_basis` is **always `null`** in Phase 5's own output (Phase 5 is purely qualitative — see Phase 6 for quantities). `action_label` is `null` unless `outcome == "ACTION_RECOMMENDED"`. `priority`/`priority_reason` are `null` for non-recommended categories; when set, `priority` is a 1-based rank among that day's `ACTION_RECOMMENDED` categories only.

---

## 7. Optimization (Phase 6) — `app/routes/optimization.py`, `app/schemas/optimization.py`

**Status: IMPLEMENTED — final testing pending** (see `docs/BACKEND_STATUS.md`).

### `GET /api/optimization/tomato/runs/{run_id}?day=`
Computed **on demand** from Phase 5's *stored* decision (never recomputes Phase 3/4/5). **404** unknown run, **422** out-of-range day.

**Response:** `OptimizationAssessmentOut`
```json
{
  "run_id": 584, "crop": "tomato", "assessment_day": 37,
  "farm_configuration": {
    "exists": true, "crop": "tomato", "field_area": 1.0, "field_area_unit": "acre",
    "plant_population": 8000, "plant_spacing_m": null, "row_spacing_m": null,
    "cultivar": "DEMO configuration (Phase 6 real-run demonstration, not a real farmer input)",
    "irrigation_system_type": "drip", "irrigation_efficiency_pct": null,
    "available_water_l_per_day": 50000.0, "pump_capacity_l_per_hour": 3000.0,
    "pump_power_kw": null, "water_cost_per_liter": 0.0005,
    "fertilizer_cost_per_kg_n": null, "fertilizer_cost_per_kg_p2o5": null, "fertilizer_cost_per_kg_k2o": null
  },
  "water_optimizations": [{
    "category": "excessive_moisture", "action_label": "Excessive Moisture", "direction": "decrease",
    "stage_name": null, "baseline_l_per_plant_day": null, "baseline_provenance": "PROJECT_DEFINED",
    "severity": "MODERATE", "adjustment_pct": 20.0, "adjustment_provenance": "PROJECT_DEFINED",
    "optimized_l_per_plant_day": null, "optimized_provenance": "MODELED",
    "plant_population": {"plants": 8000, "source": "PROVIDED", "note": "Explicit plant_population from farm configuration."},
    "baseline_l_per_day": null, "optimized_l_per_day": null,
    "water_saved_l_per_day": null, "water_saving_percentage": null,
    "review_cycle_days": 3.0, "review_cycle_provenance": "PROJECT_DEFINED",
    "total_baseline_liters": null, "total_optimized_liters": null, "total_water_saved_liters": null,
    "irrigation_efficiency_pct": 85.0, "irrigation_efficiency_source": "system_type_lookup",
    "delivered_baseline_l_per_day": null, "delivered_optimized_l_per_day": null,
    "feasibility": [
      {"label": "available_water", "status": "NOT_EVALUATED", "detail": "Required delivered field volume is unknown (plant population UNKNOWN) -- feasibility not evaluated."},
      {"label": "pump_capacity", "status": "NOT_EVALUATED", "detail": "..."}
    ],
    "cost": {"status": "UNAVAILABLE", "baseline_cost": null, "optimized_cost": null, "cost_change": null, "detail": "Field-level water quantity is unknown (plant population UNKNOWN) -- cost UNAVAILABLE."},
    "expected_direction": "FALLING", "expected_direction_basis": "MODELED EXPECTED DIRECTION",
    "limitations": ["Day 37 resolves to stage(s) ['full_cycle', 'kc_development_stage'] -- no approved baseline_irrigation parameter covers this window ..."]
  }],
  "nutrient_optimizations": [],
  "unsupported": [{"category": "heat_related", "action_label": "Address heat stress", "reason": "No quantitative resource model exists for this category ..."}],
  "multi_action_note": null,
  "limitations": ["Prototype optimization model.", "Values marked PROJECT_DEFINED are assumptions and are not scientifically validated agronomic prescriptions."]
}
```
This EXACT example is real (run 584, day 37) and shows the honest `UNAVAILABLE`/`null` case (day 37 falls in `kc_development_stage`, which has no approved baseline). **See `docs/api-examples/optimization-run-example.json` for a full non-null numeric example (run 582, day 7) instead.**

**Farmer-impact fields (added — additive only, every existing field above is unchanged):** each `water_optimizations[]` entry also carries a "typical farmer application" comparison point, alongside the existing baseline (theoretical requirement) and optimized (KAVACH recommendation) figures:
```json
{
  "typical_l_per_plant_day": 2.1, "typical_provenance": "PROJECT_DEFINED",
  "typical_application_multiplier_pct": 40.0,
  "typical_l_per_day": 16800.0,
  "water_saved_vs_typical_l_per_day": 1200.0, "water_saved_vs_typical_percentage": 7.14,
  "total_typical_liters": 50400.0, "total_water_saved_vs_typical_liters": 3600.0
}
```
`typical_l_per_plant_day` = `baseline_l_per_plant_day × (1 + typical_application_multiplier_pct / 100)` — a flat, deliberately simple **PROJECT_DEFINED** prototype heuristic (same spirit as `irrigation_adjustment_pct_*`; no sourced/measured farmer-behavior dataset exists for this project). It never changes the meaning of `baseline_l_per_plant_day` (still the theoretical crop requirement) or `optimized_l_per_plant_day` (still KAVACH's recommendation) — both keep their original, already-tested semantics. `water_saved_vs_typical_l_per_day` follows the same sign convention as `water_saved_l_per_day`: **positive = typical > KAVACH (a real saving)**, **negative = KAVACH > typical (render as "additional water required", never a saving)**. This is the intended **primary farmer-facing comparison** — `water_saved_l_per_day` (baseline vs optimized) remains available as a secondary "vs theoretical requirement" reference, not the headline metric. Seeded via `python -m app.services.optimization.seed_parameters` (`typical_application_multiplier_pct = 40`, `agronomic_parameters`, `domain=operational`, `status=project_defined`).

Field notes:
- `water_optimizations`/`nutrient_optimizations` are lists — 0, 1, or (rarely) both/multiple entries depending on how many water/nutrient categories are `ACTION_RECOMMENDED` that day. **Never assume exactly one.**
- `plant_population.source`: `enum(PROVIDED, ESTIMATED, UNKNOWN)`.
- `feasibility[].status`: `enum(PASS, FAIL, NOT_EVALUATED)`. **`NOT_EVALUATED` must never be displayed or treated as `PASS`.**
- `cost.status`: `enum(AVAILABLE, UNAVAILABLE)`.
- Every `*_provenance`/`*_basis` field is one of `SOURCED`, `PROJECT_DEFINED`, `MODELED` (or the fixed string `"MODELED EXPECTED DIRECTION"` for `expected_direction_basis`).
- `direction` (water): `enum(increase, decrease)`. `direction` (nutrient): always `"increase"`.
- Nutrient optimization object shape (see `NutrientOptimizationOut`): `category`, `nutrient` (`enum(N, P2O5, K2O)`), `action_label`, `direction`, `direction_basis`, `baseline_g_per_plant_day`, `baseline_provenance` (`"SOURCED"`), `severity`, `adjustment_pct`, `adjustment_provenance`, `optimized_g_per_plant_day`, `optimized_provenance`, `plant_population`, `total_g_per_day`, `total_kg_per_day`, `baseline_total_kg_per_day`, `duration_days`, `duration_provenance`, `total_quantity_kg`, `baseline_total_quantity_kg`, `cost`, `expected_direction`, `expected_direction_basis`, `limitations`.
- `unsupported[]` covers `ACTION_RECOMMENDED` categories with no quantitative model (heat/cold/humidity/light) — display these as Phase 5's plain qualitative recommendation, with `reason` as an explanatory note, not an error.
- `multi_action_note` is set only when **more than one** water/nutrient (quantitative) optimization exists the same day — it explains they're computed independently, never merged.

### `POST /api/optimization/tomato/runs/{run_id}/farm-config`
**Request body** (`FarmConfigurationIn`, all fields optional — send only what you want to set/change):
```json
{
  "crop": null, "field_area": 1, "field_area_unit": "acre", "plant_population": 8000,
  "plant_spacing_m": null, "row_spacing_m": null, "cultivar": null,
  "irrigation_system_type": "drip", "irrigation_efficiency_pct": null,
  "available_water_l_per_day": 50000, "pump_capacity_l_per_hour": 3000, "pump_power_kw": null,
  "water_cost_per_liter": 0.0005, "fertilizer_cost_per_kg_n": null,
  "fertilizer_cost_per_kg_p2o5": null, "fertilizer_cost_per_kg_k2o": null
}
```
`field_area_unit`: **must** be one of `acre`, `hectare`, `m2` — anything else → **422**. This is an **upsert**: first call for a run requires `field_area` + `field_area_unit`; later calls update only the fields you send, leaving the rest unchanged. **404** if `run_id` doesn't exist.

**Response:** `200 OK`, `FarmConfigurationOut` (same shape as `farm_configuration` in the GET response above, minus `exists`, plus `simulation_run_id`).

---

## PLANNED / NOT YET IMPLEMENTED

Nothing in this document is a placeholder — every endpoint above exists in the code today. What does **not** exist:

- Any Phase 7 (recommendation validation) endpoint — Phase 7 has not started.
- Any authentication/authorization layer.
- Any endpoint that lists/searches runs by scenario, crop, or date range (only `GET /api/simulator/runs` — full unfiltered list — exists).
- Any WebSocket/streaming endpoint (all APIs are request/response).
- Any endpoint to delete a run or farm configuration.
