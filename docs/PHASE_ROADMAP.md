# KAVACH — Phase Roadmap

Verified against the repository. Phase 7/8 sections describe only what's actually planned in project documentation — nothing beyond that is invented.

---

### Phase 1 — Agronomic Knowledge Base — **COMPLETE**
- **Purpose:** general/stage-specific agricultural facts with explicit provenance.
- **Input:** ICAR PDF (Phase 0) + hand-researched external sources.
- **Output:** `agronomic_parameters`, `crop_stages`, `agronomic_sources`, `stress_conditions`.
- **Modules:** `app/services/seed_agronomics.py`.
- **Frontend relevance:** secondary — a knowledge-base/sources view, not the main demo flow.

### Phase 2 — Simulation — **COMPLETE**
- **Purpose:** generate realistic virtual sensor data for a configurable scenario.
- **Input:** a `SimulationConfig` (duration, scenario, severity, seed, window).
- **Output:** `sensor_observations`, `simulation_internal_state` (not exposed).
- **Modules:** `app/services/simulator/`.
- **Frontend relevance:** run creation/selection.

### Phase 3 — State Analysis — **COMPLETE**
- **Purpose:** per-variable trend/rate/persistence/ICAR-deviation/crop-stage analysis.
- **Input:** `sensor_observations` + `tomato_reference_profile` + `crop_stages`/`agronomic_parameters`.
- **Output:** `state_analysis_history`.
- **Modules:** `app/services/state_analysis/`.
- **Frontend relevance:** dashboard/current-state view.

### Phase 4 — Problem Assessment — **COMPLETE**
- **Purpose:** evidence-gated stress detection across 10 fixed categories.
- **Input:** `state_analysis_history` (Phase 3's stored output only).
- **Output:** `problem_assessment_history`.
- **Modules:** `app/services/stress_assessment/`.
- **Frontend relevance:** "Current Problems" view.

### Phase 5 — Decision Engine — **COMPLETE**
- **Purpose:** eligibility gating, conflict detection, priority ranking, qualitative action recommendation.
- **Input:** `problem_assessment_history` (Phase 4's stored output only).
- **Output:** `decision_history`.
- **Modules:** `app/services/decision_engine/`.
- **Frontend relevance:** "Recommendations" view.

### Phase 6 — Quantitative Optimization — **IMPLEMENTED — TESTING PENDING**
- **Purpose:** baseline vs. optimized quantity, per-plant/field totals, savings, cost, feasibility for water/nutrient recommended actions.
- **Input:** `decision_history` (Phase 5's stored output only) + `farm_configurations`.
- **Output:** `optimization_history`.
- **Modules:** `app/services/optimization/`.
- **Frontend relevance:** "Optimized Plan"/"Resource Savings" view — this is the newest, least-tested layer; build the UI defensively around `null`/`UNAVAILABLE`/`NOT_EVALUATED` (see `docs/FRONTEND_GUIDE.md`).

### Phase 7 — Recommendation Validation — **NOT STARTED (FUTURE)**
Per `docs/PROJECT_STATE.md`'s own roadmap note: this section is a pointer, not an approved design. No proposal exists yet for what "validation" means concretely (comparing outcomes against the simulator's later trajectory? cross-checking against a second method?). **Do not build any frontend feature assuming specific Phase 7 behavior.**

### Phase 8 — Final Integration / Product Layer — **NOT STARTED (FUTURE)**
This is the frontend/product layer this handoff package exists to enable. No prior implementation exists; this document set is the starting point.
