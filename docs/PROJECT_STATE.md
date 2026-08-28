# KAVACH — PROJECT STATE

**This is the single source of truth for the current engineering state of
KAVACH.** It is not a README (that explains the project to a person); this
explains the current repository state to a future Claude Code session or
developer, so work can continue without re-deriving context or
misunderstanding the architecture.

**Rule for every future session, including this one on its next phase:**
Read this file first. Then verify it against the actual repository and
database. If they disagree, do not silently trust either — report the
discrepancy and resolve it before implementing anything.

**Rule for whoever finishes a phase:** update this file before considering
the phase done. It must always reflect the actual repository state, not
the plan.

Last updated: end of Phase 3 (sensor history / state analysis). Verified
against the real repository (file listing, DB row/table counts, full
test run, live CLI/API output against a real generated simulation)
rather than transcribed from memory of what should exist.

---

## 1. What we're building, and why

KAVACH is a sustainability-focused agricultural decision-support system
for tomato cultivation in a polyhouse (protected-cultivation) environment.

The problem it solves: given continuous sensor observations of a
polyhouse, detect environmental/crop problems and recommend the **minimum
necessary intervention** to keep the crop acceptable — not the
intervention that maximizes crop growth. The primary resource objective
is **water**: avoid unnecessary irrigation, avoid overwatering, detect
developing stress early, and be able to say "no intervention needed" when
that's true.

It should eventually answer questions like: "Temperature has become
dangerously high — what should the farmer do?", "Soil moisture is
falling — is irrigation actually required?", "Is the crop receiving
excessive water?", "Is current condition deviating from the expected
trajectory?" — using numerical evidence, never fabricated values.

### Non-negotiable architectural principle

**SIMULATOR = VIRTUAL SENSORS. KAVACH = DECISION/ANALYSIS SYSTEM.**

The simulator (Phase 2, **built**) generates realistic sensor
observations as if physical sensors existed in a real polyhouse. It does
**not** diagnose problems or recommend anything — it has no diagnosis
logic at all, only observation generation. KAVACH's future decision
logic (Phase 3+, not yet built) will consume those observations (or,
later, real sensor data in the identical format) and do the
diagnosis/recommendation work. The simulator's output table
(`sensor_observations`) is shaped so a future real-sensor integration
could write into it identically, without KAVACH's decision logic ever
needing to know which one produced a given row.

```
Hackathon:  virtual polyhouse -> simulator -> DB -> KAVACH -> analysis -> recommendation -> farmer
Real world: physical polyhouse -> real sensors -> DB -> KAVACH -> analysis -> recommendation -> farmer
```

### Demo observability principle (binding for all future phases)

Established at the start of Phase 3, applying to every phase from here
forward, not just Phase 3:

> Every major computational phase must expose a simple demonstration
> interface so that its inputs, processing result, and output can be
> observed during development and hackathon demonstrations. The
> demonstration interface must call the underlying phase service rather
> than duplicate its logic.

Concretely: CLI (or equivalent) -> phase service -> existing data /
previous phase's output -> structured result -> CLI presentation.
Never CLI -> duplicated phase logic. Phase 2 (`app/simulator_cli.py`)
and Phase 3 (`app/state_analysis_cli.py`) both already follow this and
are both verified by a structural test that scans the CLI module's own
source for calculation-logic fragments. Phase 4 onward must follow the
same pattern -- not built yet, but the architecture must not make a
future phase's output logic-inaccessible from the terminal.

---

## 2. Phase status

| Phase | Name | Status |
|---|---|---|
| 0 | ICAR reference data ingestion | **COMPLETE** |
| 1 | Agronomic knowledge base | **COMPLETE** |
| 1.5B | Agronomic source audit (research only) | **COMPLETE** |
| 1.5C | Apply verified agronomic knowledge | **COMPLETE** |
| 2A | Virtual sensor simulator design (proposal + revisions) | **COMPLETE (approved)** |
| 2 | Virtual sensor simulator implementation | **COMPLETE** |
| 2.1 | Simulator CLI (terminal interface) | **COMPLETE** |
| 3 | Sensor history / state analysis | **COMPLETE** |
| 4 | Problem / stress detection | NOT STARTED (next) |
| 5 | Intervention modelling | NOT STARTED |
| 6 | Sustainability / resource optimization | NOT STARTED |
| 7 | Recommendation validation | NOT STARTED |
| 8 | Farmer-facing API/UI | NOT STARTED |

Do not assume any phase past 1.5C is designed or implemented just because
it appears in this roadmap. Each phase gets reviewed and approved before
implementation, same as 0 through 1.5C were.

---

## 3. Repository layout (actual, verified)

```
kavach/
├── data/
│   ├── sources/icar/tomato_reference.pdf      Phase 0 source PDF (FROZEN)
│   ├── seed/tomato_reference.csv              Phase 0 extracted/verified CSV (FROZEN)
│   └── backups/kavach.db.phase1_5c_backup_*   pre-Phase-1.5C DB snapshot
├── backend/
│   ├── kavach.db                              SQLite DB (build artifact, not a source of truth)
│   ├── requirements.txt, pytest.ini
│   ├── app/
│   │   ├── main.py                            FastAPI app, includes both routers
│   │   ├── simulator_cli.py                   Phase 2.1 -- terminal UI only, no simulation logic of its own
│   │   ├── database/session.py                SQLAlchemy engine/session/Base
│   │   ├── models/
│   │   │   ├── tomato_reference.py            TomatoReferenceProfile (Phase 0)
│   │   │   ├── data_source.py                 DataSource (Phase 0 provenance)
│   │   │   ├── agronomic_source.py            AgronomicSource (Phase 1)
│   │   │   ├── crop_stage.py                  CropStage (Phase 1)
│   │   │   ├── agronomic_parameter.py         AgronomicParameter (Phase 1, extended 1.5C)
│   │   │   ├── stress_condition.py            StressCondition (Phase 1)
│   │   │   ├── agronomic_status.py            NOT a DB table -- shared status-string constant used by AgronomicParameter/StressCondition and mirrored in the Pydantic schema
│   │   │   ├── simulation_run.py              SimulationRun (Phase 2)
│   │   │   ├── sensor_observation.py          SensorObservation (Phase 2)
│   │   │   ├── simulation_internal_state.py   SimulationInternalState (Phase 2, debug/traceability only)
│   │   │   └── state_analysis_history.py      StateAnalysisHistory (Phase 3, one row per run-day)
│   │   ├── schemas/
│   │   │   ├── tomato_reference.py            TomatoReferenceProfileOut
│   │   │   ├── agronomics.py                  AgronomicSourceOut, CropStageOut, AgronomicParameterOut, StressConditionOut
│   │   │   ├── simulator.py                   SimulationRunCreate, SimulationRunOut, SensorObservationOut
│   │   │   └── state_analysis.py              StateAnalysisOut and nested Out schemas (Phase 3, API boundary only)
│   │   ├── routes/
│   │   │   ├── reference.py                   /api/reference/tomato...
│   │   │   ├── agronomics.py                  /api/agronomics/tomato...
│   │   │   ├── simulator.py                   /api/simulator/runs...
│   │   │   └── state_analysis.py              /api/analysis/tomato/runs/{run_id}... (Phase 3)
│   │   ├── state_analysis_cli.py              Phase 3 -- terminal UI only, no analysis logic of its own
│   │   └── services/
│   │       ├── extract_reference.py           PDF -> CSV extraction + validation (Phase 0)
│   │       ├── seed_database.py               CSV -> tomato_reference_profile (Phase 0)
│   │       ├── seed_agronomics.py             sources/stages/parameters/stress_conditions (Phase 1 + 1.5C)
│   │       ├── simulator/
│   │       │   └── run_service.py             Phase 2 -- create_run() also calls Phase 3's persist_run_history() (the ONE Phase 2 file touched by Phase 3; no generation-equation file touched)
│   │       └── state_analysis/                Phase 3 -- see section 4 for the module breakdown (includes history.py: Workflow A persistence + Workflow B's read path)
│   └── tests/
│       ├── conftest.py                        seeded_db, seeded_agronomics_db, api_client fixtures (imports app.main early so ALL models are registered before any create_all() call)
│       ├── test_extraction.py                 Phase 0
│       ├── test_database_and_api.py           Phase 0
│       ├── test_agronomics.py                 Phase 1 + 1.5C
│       ├── test_simulator.py                  Phase 2
│       ├── test_simulator_cli.py              Phase 2.1
│       ├── test_state_analysis.py             Phase 3
│       └── test_state_analysis_cli.py         Phase 3
├── docs/
│   ├── agronomic_parameter_audit.md           Phase 1.5B research report
│   └── PROJECT_STATE.md                       this file
└── README.md
```

No `frontend/`, no `decision_engine`, no `optimizer`, no `validator`, no
LLM/ML/RL code anywhere in the repo. `simulator` legitimately exists now
(Phase 2). This is enforced by an actual test
(`test_no_decision_engine_or_llm_modules_exist` in `test_agronomics.py`,
renamed and narrowed from its Phase-1 version when Phase 2 landed), not
just a claim in this document.

---

## 4. What's been completed

### Phase 0 — ICAR reference data (FROZEN, do not modify without explicit instruction)

- Source PDF: `data/sources/icar/tomato_reference.pdf` (5 pages, Day
  1-120 tomato polyhouse table). Checksum-verified unchanged after every
  later phase.
- Extracted, validated CSV: `data/seed/tomato_reference.csv` — 120 rows,
  days 1-120 exactly once each, no blanks/malformed cells. Columns:
  `day, soil_moisture_pct, temperature_c, humidity_pct,
  dli_mol_m2_day, soil_n_mg_kg, soil_p_mg_kg, soil_k_mg_kg,
  n_demand_g_plant_day, p2o5_demand_g_plant_day, k2o_demand_g_plant_day`.
- DB table `tomato_reference_profile`: 120 rows, seeded from the CSV
  (never from the PDF directly), reproducible via
  `python -m app.services.seed_database`.
- DB table `data_source`: 1 row, Phase-0-specific provenance record for
  the PDF (distinct from the richer `agronomic_sources` table added in
  Phase 1).
- API: `GET /api/reference/tomato`, `GET /api/reference/tomato/day/{day}`
  (404 outside 1-120).
- Day 47 and Day 120 are pinned by regression tests that cross-check
  CSV -> raw SQLite -> ORM -> Pydantic -> live API JSON are all identical
  — re-verified after every subsequent phase.

**This is a reference profile, not live sensor data, not a "ground
truth" label, not a recommendation table.**

### Phase 1 — Agronomic knowledge base

Built a knowledge layer separate from the day-by-day reference profile:
general/stage-specific agricultural facts with explicit provenance and
an explicit status per fact, so a sourced value can never look identical
to a guess.

Tables: `agronomic_sources`, `crop_stages`, `agronomic_parameters`,
`stress_conditions`.

API:
```
GET /api/agronomics/tomato/sources
GET /api/agronomics/tomato/stages
GET /api/agronomics/tomato/stages/{stage_id}
GET /api/agronomics/tomato/parameters          (filters: ?status=, ?domain=)
GET /api/agronomics/tomato/parameters/{parameter_name}
GET /api/agronomics/tomato/stress-conditions
```
These expose agricultural facts and their sourcing status only — no
diagnosis, no recommendation.

### Phase 1.5B — Agronomic source audit (research only, no DB changes)

Web-researched all 23 parameters that were `missing`/`source_needed`
after Phase 1, against FAO / ICAR-adjacent / USDA-NRCS / peer-reviewed /
university-extension sources only (commercial/blog/SEO sources excluded
from evidence, named only where encountered). Full report:
`docs/agronomic_parameter_audit.md`.

Key finding: the tomato Kc values previously only "discussed" —
initial 0.53, mid 1.08, late 0.63 — turned out to be real, verified
against **Sharma & Changade (2025)**, *Journal of Agrometeorology*
27(2):157-162, a peer-reviewed study measuring Kc specifically in a
naturally-ventilated **polyhouse** in Jalandhar, Punjab — a close
contextual match to KAVACH.

Key gap found and reported honestly: a previously-referenced "22/26°C
optimum, ≥35°C day/≥26°C night screening" ICAR figure could **not** be
verified against any source found. The closest real ICAR-adjacent
literature located (ICAR-IIVR Varanasi heat-tolerance screening,
2013-2016) uses a different, separately-unverified 32°C day/26°C night
regime instead. Neither pair is stored as fact in the DB.

### Phase 1.5C — Apply verified agronomic knowledge (DB rebuilt)

Schema: added `value_min`/`value_max` (nullable Float) to
`agronomic_parameters`, plus a DB-level `CHECK` constraint that
`value_numeric` and `value_min` can never both be populated on the same
row (verified by a test that actually triggers `IntegrityError`, not
just a convention). Extended `AGRONOMIC_STATUS_VALUES` from 4 to 6:
`sourced, assumption, missing, source_needed, derived, context_dependent`.

Stage association uses the real `stage_id` FK to `crop_stages` — never a
stage name in a text field. Two independent stage taxonomies coexist,
each tied to its own `source_id`: Sharma & Changade's 4 DAS-based Kc
stages (real day windows) and DAF Qld's 4 phenological stages (no
day-number mapping given by that source, so left NULL rather than
invented), plus the original `full_cycle` (Day 1-120, ICAR-derived).

`backend/kavach.db` was fully deleted and rebuilt from the seed scripts
(no Alembic in this project — SQLite `create_all` doesn't ALTER existing
tables, so a full rebuild from source-of-truth Python/CSV was the correct
mechanism, not a manual schema patch). A pre-rebuild backup was taken
first: `data/backups/kavach.db.phase1_5c_backup_20260824_014234`.

Current DB contents (verified by direct query, not assumed):

| Table | Rows |
|---|---|
| `tomato_reference_profile` | 120 |
| `data_source` | 1 |
| `agronomic_sources` | 11 |
| `crop_stages` | 9 |
| `agronomic_parameters` | 40 |
| `stress_conditions` | 5 |

Of the 40 `agronomic_parameters` rows: 27 `status="sourced"` (real values
with full provenance), 3 `status="derived"` (computed quantities,
values permanently NULL), 4 `status="context_dependent"` (site/config
facts, values permanently NULL), 2 `status="source_needed"` (no credible
source found, values NULL). See section 6 for exactly which.

`stress_conditions` (5 rows: water_stress, excessive_soil_moisture,
heat_stress, humidity_stress, nutrient_imbalance) were **not** touched in
1.5C — still knowledge-only placeholders with NULL thresholds, unchanged
since Phase 1. Wiring the newly-sourced temperature thresholds into
`heat_stress` was explicitly deferred, not done silently.

Tests: 37/37 passing at the time. PDF checksum and CSV line count
re-verified unchanged after the rebuild.

### Phase 2 — Virtual sensor simulator

Built exactly to a proposed-and-approved design (Phase 2A proposal, one
revision round, one final calibration requirement — all approved before
any code was written). Generates realistic 6-hour-resolution virtual
sensor observations; does **not** diagnose, recommend, or optimize
anything.

**New tables** (all new, no Phase 0/1 table touched):
- `simulation_runs` — one row per generated run: `crop, duration_days,
  scenario, severity, seed, scenario_start_day, scenario_duration_days,
  created_at`. Immutable once created; "regenerate" = create a new run.
- `sensor_observations` — one row per 6-hour reading: `simulation_run_id,
  day, hour (0/6/12/18), temperature_c, humidity_pct, soil_moisture_pct,
  daily_dli_mol_m2_day, soil_n_mg_kg, soil_p_mg_kg, soil_k_mg_kg`. Shaped
  to be indistinguishable from a future real-sensor feed.
  `daily_dli_mol_m2_day` is ICAR's daily figure duplicated across all 4
  of that day's rows — never a synthesized instantaneous reading.
  Demand fields (`n_demand_g_plant_day` etc.) are intentionally NOT
  simulated — no physical sensor measures "demand."
- `simulation_internal_state` — debug/traceability only (never exposed
  as a recommendation): `irrigation_input_pct, evaporative_loss_pct,
  temperature_delta_from_scenario, humidity_delta_from_scenario` per
  slot. Kept separate from `sensor_observations` so that table stays a
  clean "what a real sensor would report" shape.

**Simulator module** (`backend/app/services/simulator/`):
- `constants.py` — every simulator-internal number (diurnal amplitude,
  temp/humidity coupling, evaporative-loss proxy coefficients, per-
  severity scenario magnitudes, safety clamp bounds, noise magnitudes).
  Every single one is a **MODEL ASSUMPTION**, none has a `source_id`,
  none should ever be confused with `agronomic_parameters`.
- `rng.py` — deterministic per-variable seeded streams (uses `hashlib`,
  not builtin `hash()`, because Python randomizes string hashing
  per-process by default — using `hash()` would have silently broken
  cross-run reproducibility).
- `baseline.py` — read-only loader of the ICAR reference trajectory.
- `causal_model.py` — diurnal temperature shape, temp→humidity coupling,
  the simplified evaporative-loss proxy. Explicitly **not** FAO-56/
  Penman-Monteith — a documented simplification.
- `calibration.py` — the approved NORMAL-scenario calibration mechanism:
  for each ICAR day, derives the daily irrigation input that would (given
  the simplified evap model) move that day's ICAR moisture toward the
  next day's ICAR moisture, clamped to a physically reasonable bound
  (never solved to force an exact match — see MODEL ASSUMPTION text
  quoted in the module docstring, matching the user-approved wording
  verbatim).
- `scenarios.py` — per-scenario temperature/humidity/irrigation-multiplier
  forcing functions (heatwave, water_shortage, excess_irrigation,
  high_humidity), each with exactly one internal cause.
- `config.py` — `SimulationConfig` + validation (duration 1-120, severity/
  window required iff scenario≠normal, window can't exceed duration).
  No FastAPI/Pydantic dependency, so the simulator core is testable
  standalone.
- `generator.py` — orchestrates generation. Soil moisture is the one
  genuinely stateful variable, carried as one continuous value across
  the whole run, anchored to the real ICAR value only once (day 1, hour
  0) — never hard-reset daily, which is what lets a multi-day scenario
  compound instead of "healing" every midnight. N/P/K use linear
  interpolation between consecutive ICAR days, not independent modeling.
- `run_service.py` — persists a run + its observations + its internal
  state via SQLAlchemy.

**API**: `POST /api/simulator/runs`, `GET /api/simulator/runs`,
`GET /api/simulator/runs/{id}`, `GET /api/simulator/runs/{id}/observations`
(optional `?day=` filter).

**Two real bugs found and fixed during implementation** (via manual
smoke-testing before trusting the automated tests):
1. Day-1's hour-0 temperature/humidity were initially left flat (no
   diurnal offset) as a mistaken side-effect of anchoring soil moisture
   there — created an artificial discontinuity vs. day 2/3's midnight
   readings. Fixed: only soil moisture gets the literal ICAR anchor;
   temperature/humidity/N/P/K follow the same formula every hour,
   including day 1 hour 0.
2. **Irrigation-share bookkeeping was off by one day.** Each day's
   calibrated irrigation is meant to bridge that day's ICAR moisture to
   the *next* day's ICAR moisture — so it must be spread across the 4
   transitions *originating from* that day's own slots (3 landing within
   the same day, 1 landing on the next day's hour-0). It was initially
   implemented as "spread across the 4 transitions *arriving at* that
   day's own slots" instead, which front-loaded an entire day's
   irrigation into that same day's own readings. This was caught by the
   very sanity check the approved calibration requirement implies: ICAR
   day 28→29 has a real +3-point jump, and the simulator was showing
   that jump's irrigation already inflating day 28 itself.
3. **Soil moisture noise was being fed back into the running state**,
   turning it into a random walk whose drift grows with the square root
   of run length — for a 60-day run this produced multi-point
   seed-dependent drift, undermining the whole point of the NORMAL
   calibration. Fixed: the state (`true_moisture`) evolves purely from
   evap+irrigation with no noise; a separate small noise draw is added
   only to the *reported* value per slot, never re-injected into the
   state. After the fix, worst-case drift over a 60-day NORMAL run
   dropped from ~7 points to ~1.5 points for the seeds tested.

Tests: 60/60 passing at the time.

### Phase 2.1 — Simulator CLI

A thin terminal front-end for the simulator, `backend/app/simulator_cli.py`
— `python -m app.simulator_cli` — for demoing/operating the simulator
without the API server, curl, or JSON. **Contains no simulation logic of
its own**; it only calls `app.services.simulator.config.build_config`
and `app.services.simulator.run_service.create_run`, then formats the
resulting `SensorObservation` rows as terminal tables. This is verified
structurally by a test that scans the CLI module's source for
generation-logic fragments (`evaporative_loss`,
`diurnal_temperature_offset`, etc.) and fails if any are found.

Two modes:
- **Interactive generate** (`python -m app.simulator_cli`, no args):
  prompts for duration/scenario/(severity+window if non-normal)/seed,
  generates a real run, then prints a checklist confirmation, first-day
  and last-day tables, and temperature/soil-moisture summary stats (min/
  max/average) — never all observations at once.
- **View one day** (`--run-id N --day D`): prints just that day's 4
  observations in the same table format.

Bad input (non-numeric, out-of-range duration/menu-choice/day) is
reprompted or reported with a clean `✗ ...` message — never a Python
traceback.

**One real bug found and fixed during implementation**: Windows consoles
(cmd.exe/PowerShell) commonly default to a legacy codepage (e.g. cp1252)
that cannot encode the ✓/✗/box-drawing characters used in the output —
printing them would have crashed the CLI with `UnicodeEncodeError` on
the very platform this tool is for. Fixed by forcing UTF-8 on
stdout/stderr at startup (`sys.stdout.reconfigure(encoding="utf-8", ...)`).

Tests: 60 -> 74 passing (see section 8; this count corrects a stale "68"
that had drifted from the actual `test_simulator_cli.py` test count by
the time Phase 3 started -- see the note at the end of section 8).

### Phase 3 — Sensor history / state analysis

Built exactly to the approved Phase 3 proposal: a read-only analysis
layer over Phase 2's `sensor_observations`, Phase 0's
`tomato_reference_profile`, and Phase 1/1.5C's `crop_stages`/
`agronomic_parameters`. **No decision-making, diagnosis, or
recommendation logic** -- verified structurally by tests, not just by
convention.

**What it computes, per sensor variable (temperature, humidity, soil
moisture, DLI, soil N/P/K), scoped to one `simulation_run_id`:**

- **Current state**: the value at the single latest (day, hour)
  observation in the analysis window.
- **Trend** (`app/services/state_analysis/trend.py`): an ordinary
  least-squares (OLS) regression of the variable against actual
  elapsed time in days (`day + hour/24`), not observation index --
  this is what makes the slope directly a per-day rate and keeps the
  method valid against irregular future real-sensor timestamps, not
  just the simulator's fixed 6-hour grid. Direction (RISING / FALLING
  / STABLE) is decided by comparing the fitted slope against a
  **stability band derived from the regression's own residual noise**
  (`STABILITY_K = 2.0` times the slope's standard error -- an
  approximate 95% two-sided significance test, the standard OLS
  convention for "is this slope distinguishable from zero given this
  window's own noise level"). This is an **analytical/statistical
  constant, not an agronomic fact**, and is documented in code exactly
  as required. Needs at least 3 observations (residual variance needs
  n-2 >= 1 degrees of freedom); fewer are reported as
  `UNDETERMINED`, never guessed.
- **Rate of change**: the same OLS slope, always reported per day with
  an explicit unit per variable (°C/day, %/day, pp/day for soil
  moisture, mg/kg/day, mol/m²/day/day for DLI) -- 6-hour and daily
  cadence are never conflated.
- **Trend persistence** (`app/services/state_analysis/persistence.py`):
  day-level averages (not raw 6-hour readings, so a single noisy
  reading can never flip the count), walking backward from the latest
  day while the day-over-day delta stays consistent with the reported
  direction, using the SAME stability band computed for trend --
  no second, separately invented threshold. Short histories (<2 days)
  are reported as undetermined, not fabricated.
- **ICAR reference deviation** (`app/services/state_analysis/icar_deviation.py`):
  reuses `app.services.simulator.baseline.load_baseline` -- the
  EXISTING Phase 0 reference loader, not a new one -- to compare the
  current value against the actual ICAR value for the same day.
  Reports current value, ICAR value, signed difference, absolute
  difference, unit. Never extrapolates past ICAR's day 1-120 range;
  reports "unavailable" with an explicit note instead.
- **Crop-stage context** (`app/services/state_analysis/crop_stage_context.py`):
  matches the analysis day against the EXISTING `crop_stages` table's
  day-mapped stages only (`full_cycle` + the 4 Sharma & Changade Kc
  stages) -- the DAF Qld phenological stages (germination, etc.) have
  no day mapping in the source data and are never guessed into one.
  **Day 100 falls in both `kc_mid_stage` (ends day 100) and
  `kc_late_stage` (starts day 100) as literally sourced from Sharma &
  Changade (2025)'s own table -- both are returned, never silently
  narrowed to one.**
- **Agronomic context**: `agronomic_parameters` rows whose `stage_id`
  matches a resolved (day-mapped) stage -- today this only yields real
  content for the `water` domain (Kc values), since temperature/
  humidity/DLI/soil thresholds are linked only to the day-less DAF Qld
  stages. Reported honestly as unavailable rather than invented -- see
  Known Limitations.
- **Data-quality notes**: missing days, partial days (<4 of 4 expected
  6-hour slots), and out-of-range percentage values. Out-of-range
  flagging is deliberately restricted to `humidity_pct`/
  `soil_moisture_pct` (0-100% is a mathematical certainty, not an
  agronomic judgment) -- temperature/N/P/K have no such
  universally-true bound and are not flagged, to avoid inventing an
  agronomic threshold. These notes state facts only, never a cause or
  an action.

**Persistence decision (revised after initial Phase 3 implementation)**:
Phase 3 is split into two deliberately separate workflows, and DOES now
persist -- a new table, `state_analysis_history`, one row per
`(simulation_run_id, day)` for the ENTIRE run (a 60-day run -> exactly
60 rows, never 240). Reason for the revision: the original
calculate-on-demand design was correct for a single CLI/API lookup, but
Phase 4 needs to scan a run's whole history without replaying the
regression for every day on every access, and "automatically process a
completed simulation" (this session's requirement) needs somewhere to
put that output. Per-parameter/stage/context detail is stored as JSON
(`parameters_json`, `crop_stages_json`, `agronomic_context_json`,
`data_quality_notes_json`) -- a direct `dataclasses.asdict` dump of
`analyze_run`'s own result, never a second, independently maintained
representation. No Alembic still applies here too: this is a brand-new
table (`create_all` handles it), not an ALTER of an existing one.

- **WORKFLOW A -- backend persistence**
  (`backend/app/services/state_analysis/history.py`):
  `persist_run_history(db, run_id)` computes `analyze_run(db, run_id,
  day=d)` for every `d` in `1..duration_days` and stores one
  `state_analysis_history` row per day (idempotent -- deletes any
  existing rows for that `run_id` first, mirroring
  `seed_agronomics.py`'s own delete-then-reinsert convention). This is
  now called **automatically**, once, at the end of
  `app.services.simulator.run_service.create_run()` -- the single
  common path both `POST /api/simulator/runs` and `python -m
  app.simulator_cli` already funnel every successful run through, so
  no other Phase 2 call site needed touching. It only runs after that
  run's `sensor_observations` are already committed; if it raises, the
  exception propagates out of `create_run()` unmodified (the
  already-committed Phase 2 data is NOT rolled back -- runs are
  immutable/append-only by this project's convention -- but the
  overall call reports failure rather than silently claiming Phase 3
  history exists when it doesn't). `history.py` also keeps its own
  `python -m app.services.state_analysis.history --run-id N` entrypoint
  as a manual/backfill tool (e.g. for runs created before this
  automatic wiring existed) -- it is no longer the normal way this
  table gets populated.
- **WORKFLOW B -- demo/observability**
  (`backend/app/state_analysis_cli.py`, `python -m
  app.state_analysis_cli --run-id N [--day D]`): presentation-only,
  calls `get_stored_analysis(db, run_id, day=D)` (also in
  `history.py`) and formats the result -- it NEVER calls `analyze_run`
  itself and is NOT responsible for creating history. If nothing has
  been persisted for the requested run/day, it says so explicitly
  (naming the manual backfill command) and exits 1 rather than
  computing a fallback. `--day D` is view/filter only -- it reads
  whichever day's row already exists; it never populates the database.
  Verified structurally by a test that scans the CLI's source for
  calculation-logic fragments (`sxx`, `STABILITY_K`,
  `def compute_trend(`, etc.) the same way `simulator_cli.py` is
  checked, plus a test that it never imports `analyze_run` at all
  (only `get_stored_analysis`).

**API**: `GET /api/analysis/tomato/runs/{run_id}` and `?day=D` are
UNCHANGED from the original design -- still calculate on demand via
`analyze_run` directly (404 for an unknown run, 422 for an
out-of-range day). This was a deliberate scope decision, not an
oversight: the automatic-persistence requirement was specifically
about the CLI/backend pipeline; whether the API route should also
switch to reading `state_analysis_history` is an open question for a
future session, not decided here.

**Module** (`backend/app/services/state_analysis/`): `parameters.py`
(shared 7-variable registry), `current_state.py`, `trend.py`,
`persistence.py`, `icar_deviation.py`, `crop_stage_context.py`
(crop-stage AND agronomic-context resolution), `service.py`
(`analyze_run(db, run_id, day=None)` -- the on-demand calculation,
still used by the API and by Workflow A internally; raises
`RunNotFoundError`/`InvalidDayError`, both subclasses of
`StateAnalysisError`), `history.py` (Workflow A + Workflow B's read
path, described above). New model:
`backend/app/models/state_analysis_history.py` (`StateAnalysisHistory`).

**One real bug found and fixed while wiring the automatic trigger**:
`persist_run_history()` commits internally on the same SQLAlchemy
session `create_run()` passes it. SQLAlchemy's default
`expire_on_commit=True` means that internal commit re-expired the
already-`db.refresh()`-ed `run` object a second time, so `create_run()`
was handing callers back an expired object -- any caller reading one of
its attributes AFTER closing their own session hit
`DetachedInstanceError`. Fixed with one more `db.refresh(run)` after
the `persist_run_history()` call, restoring the "fully loaded, safe to
read after close" guarantee `create_run()` already gave before Phase 3
was wired in. Found via the test suite (10 tests failed with this
exact error before the fix), not via manual testing.

No bugs were found in Phase 0/1/2 during either the original Phase 3
implementation or this automatic-trigger integration. `run_service.py`
is the one Phase 2 file modified -- a two-line addition (an import and
one function call) plus the one-line refresh fix above, at the single
point every successful run already passes through; no simulator
generation file (`generator.py`, `causal_model.py`, `calibration.py`,
`scenarios.py`, `constants.py`, `rng.py`, `baseline.py`) was touched,
and no equation/behavior of the simulator itself changed.

---

## 5. Agronomic data representation rules (apply to all future agronomic work)

- **Single sourced value** → `value_numeric` set, `value_min`/`value_max`
  NULL.
- **Sourced range** → `value_min` + `value_max` set, `value_numeric`
  NULL. Never collapsed to a midpoint.
- **Stage-specific value** → real `stage_id` FK to a `crop_stages` row.
  Never a stage name in `notes` or `context`.
- **Provenance** → real `source_id` FK to `agronomic_sources`. A
  `status="sourced"` row always has a non-null `source_id`; a
  `status="missing"`/`"source_needed"` row always has `source_id=NULL`.
- **Computed quantities never get stored as facts** — `status="derived"`,
  value fields permanently NULL, the formula/inputs documented in
  `notes`. Current derived concepts: `eto_reference_mm_day`,
  `crop_water_requirement_mm_day`, `soil_available_water_capacity_mm`.
  These get calculated by a future water-requirement service, not looked
  up here.
- **Site/config-specific facts never get a universal number** —
  `status="context_dependent"`, value fields permanently NULL. Current
  context-dependent concepts: `soil_texture`, `soil_field_capacity_pct`,
  `soil_permanent_wilting_point_pct`, `irrigation_efficiency_pct`. These
  belong to a future soil-profile / irrigation-system configuration
  model (not built — no real farm is configured yet), not to
  `agronomic_parameters`.
- **Never invent a value to fill a gap.** A `source_needed`/`missing` row
  with `value=NULL` is correct and expected — it is not a bug to fix by
  guessing.

---

## 6. Current agronomic_parameters contents (40 rows, by status)

**`sourced` (27 rows)**: `kc_initial` / `kc_mid` / `kc_late` (3 rows each
— polyhouse/shade-net/open-field variants from Sharma & Changade 2025;
9 rows total) · `temperature_min_c` (4 rows, one per DAF-Qld stage) ·
`temperature_max_c` (5 rows — germination has 2 rows because the source's
own table and body text disagree, both preserved rather than averaged) ·
`temperature_critical_stress_c` (4 context rows, heat-stress review) ·
`humidity_min_pct` / `humidity_max_pct` (1 range row each, Shamshiri
2018) · `dli_target_mol_m2_day` transplant-stage row (1 range row,
Purdue) · `root_zone_depth_cm` (1 range row, FAO-56) · `soil_ph` (1 range
row, Rutgers) · `soil_ec_ds_m` (1 point row, FAO) ·
`n_total_requirement_g_plant_season` / `p2o5_total_requirement_g_plant_season`
/ `k2o_total_requirement_g_plant_season` (1 row each, TNAU — stored as
`value_text` + `unit="kg/ha"` because the source is per-hectare and
converting to per-plant needs KAVACH's plant population, which isn't
configured; not silently converted).

**`derived` (3 rows, values NULL)**: `eto_reference_mm_day`,
`crop_water_requirement_mm_day`, `soil_available_water_capacity_mm`.

**`context_dependent` (4 rows, values NULL)**: `soil_field_capacity_pct`,
`soil_permanent_wilting_point_pct`, `soil_texture`,
`irrigation_efficiency_pct`.

**`source_needed` (2 rows, values NULL)**: `soil_bulk_density_g_cm3`,
`dli_target_mol_m2_day` mature-production-stage row (only commercial
LED-vendor sources were found for this one — explicitly excluded).

---

## 7. Sources currently in `agronomic_sources` (11)

ICAR tomato polyhouse dataset (Phase 0's PDF, catalogued here too) ·
Sharma & Changade (2025, polyhouse Kc, Jalandhar) · FAO-56 / Allen et al.
1998 (ETo methodology, root-zone depth) · DAF Qld / Deuter & Carey 2023
(temperature thresholds, open-field, Queensland) · Shamshiri et al. 2018
(greenhouse T/RH/VPD review) · Purdue / Wuetcher & Owen 2025 (DLI,
transplant stage) · Rutgers NJAES FS678 (soil pH) · FAO Annex 1 (soil
salt tolerance) · TNAU fertigation schedule (N/P₂O₅/K₂O) · USDA NRCS
soil-water convention (field capacity / wilting point definitions —
definitional only, no per-texture value table retrieved) · a compiling
heat-stress review, PMC7938145 (temperature_critical_stress_c).

Every `status="sourced"` or `status="derived"`/`"context_dependent"`-with-
a-definitional-citation row references one of these by `source_id`.
Nothing is cited that isn't in this table.

---

## 8. Current test status

**140/140 passing** as of end of Phase 3's automatic-pipeline
integration (`backend/tests/`, run via `pytest tests/ -v` from
`backend/`). Up from 122 at the end of Phase 3's original
(calculate-on-demand) implementation -- the persistence pivot
(`state_analysis_history` + Workflow A/B split + the automatic
`create_run()` trigger) added `test_state_analysis_history.py` (14
new) and grew `test_state_analysis_cli.py` from 8 to 12 (net +4: some
tests were updated in place for the new "history is now automatic"
reality rather than added).

*Correction*: this document previously claimed "68/68 passing" as of
end of Phase 2.1. Verified against the actual repository at the start
of Phase 3: `test_simulator_cli.py` actually contains 14 tests, not 8
-- the true Phase 2.1 count was 74, not 68. All 74 passed; this was a
documentation drift, not a code defect, and is corrected here rather
than silently carried forward.

- `test_extraction.py` (7): PDF exists, CSV exists, row count, day
  range/no dupes, column names match verified PDF structure, numeric
  parse, deterministic re-extraction matches committed CSV.
- `test_database_and_api.py` (9): DB record count matches CSV, day range,
  DB values match CSV, API day 1/47/120/121, full Day-47
  CSV/SQLite/ORM/Pydantic/API cross-check, full-list endpoint.
- `test_agronomics.py` (21): source CRUD/retrieval, two-taxonomy stage
  structure, stage FK linkage, status/source_id consistency rules,
  provenance-never-lost, value-exclusivity (API-level and an actual
  `IntegrityError`-triggering DB-level test), ranges never collapsed to a
  midpoint, DAF Qld's germination conflict preserved as 2 rows, Kc fully
  sourced with provenance, P≠P₂O₅ and K≠K₂O held distinct, unresolved
  params stay NULL, derived/context-dependent params never store a
  value, stress-conditions present with NULL thresholds, Phase 0 Day
  47/120 unchanged, Phase 0 endpoints still work, **structural guard**
  that no decision-engine/optimizer/validator/LLM module exists anywhere
  under `app/` (simulator is now allowed and excluded from this guard).
- `test_simulator.py` (23): config validation (duration bounds,
  severity/window requirements, window-can't-exceed-duration), row
  count/day-hour coverage, DLI is one value per day not four independent
  readings, determinism (same config twice ⇒ identical), different seed
  ⇒ different output, each of the 4 scenarios causally diverges from
  NORMAL in exactly its documented way (heatwave raises temp AND
  accelerates moisture decline; water_shortage lowers moisture without
  touching temp/humidity; excess_irrigation raises moisture toward the
  ceiling; high_humidity raises humidity without touching moisture
  directly), moisture/humidity never leave [0,100], NORMAL scenario
  tracks the ICAR trajectory within a documented tolerance, full API
  create/retrieve/list/filter/404 coverage, reproducibility via the API,
  Phase 0/1 endpoints still work.
- `test_simulator_cli.py` (14): generates a real simulation end-to-end,
  40 days -> exactly 160 observations via the CLI, `--day` shows exactly
  4 observations, invalid/non-numeric input is reprompted rather than
  crashing, nonexistent run and out-of-range day both fail with a clean
  `✗` message (not a traceback), `--day` without `--run-id` (or vice
  versa) fails cleanly, full-dataset terminal dump shows every day in
  chronological order with exactly 4 slots each, the summary block
  appears after all day tables, no raw Python/JSON objects leak into
  the output, `--day` still works unchanged alongside the full-dump
  feature, and a structural check that the CLI module contains no
  simulation logic of its own.
- `test_state_analysis.py` (40): trend math (UNDETERMINED below the
  minimum-observations floor, RISING/FALLING/STABLE against synthetic
  signals, the degenerate-same-elapsed-time case), persistence math
  (consecutive-day counting matching the spec's own worked example,
  undetermined below 2 days, undetermined when trend is undetermined),
  ICAR deviation math (signed/absolute difference, unavailable outside
  day 1-120), crop-stage resolution (day 100's real overlap returns
  BOTH `kc_mid_stage` and `kc_late_stage`, the DAF Qld day-less stages
  are never matched by day), agronomic-context resolution (all 3 Kc
  context variants returned for a matched stage, empty list for no
  stage), data-quality notes (missing days, partial days, out-of-range
  percentages only, clean data produces no notes), full-service
  integration against a real generated simulation (all 7 parameters
  present, `--day` restricts history, invalid run id / invalid day
  raise the correct typed errors, single-day runs report undetermined
  persistence, multiple runs stay isolated, repeated calls are
  deterministic, ICAR deviation matches the actual reference row, day
  100 reports both stages, the temperature domain has no
  day-resolvable agronomic context), full API coverage (200 with full
  structure, `?day=` filter, 404 for an unknown run, 422 for an
  out-of-range day, CLI and API agree on the same underlying analysis
  for the same run), and structural guards (CLI contains no
  calculation logic, the route contains no calculation logic, the
  `state_analysis` package never imports simulator-internal modules or
  `simulation_internal_state`, no diagnosis/recommendation vocabulary
  anywhere in the Phase 3 source OR in actual rendered CLI output from
  a real heatwave-scenario run).
- `test_state_analysis_cli.py` (12): a run created through the normal
  path already has Phase 3 history (the automatic-trigger requirement,
  asserted directly against `state_analysis_history` row counts), the
  CLI refuses and names the manual backfill command when history is
  genuinely absent (simulated by deleting the auto-created rows) rather
  than computing a fallback, `--day` never populates the database even
  when history is absent, full analysis prints for a real persisted run
  with every required section header present, `--day` at two different
  days reads the matching persisted day, nonexistent run and
  out-of-range day both fail cleanly with `✗`, missing `--run-id` is
  rejected by argparse, day 100 visibly shows both overlapping stages
  with an explicit overlap note, an ordinary day (regression test) does
  NOT falsely claim an overlap just because `full_cycle` always
  co-matches, no raw Python objects leak into the output, and a
  structural check that the CLI reads `get_stored_analysis` and never
  imports `analyze_run` (Workflow A's per-day compute entrypoint)
  outside its own docstring.
- `test_state_analysis_history.py` (14): `persist_run_history` writes
  exactly one row per day (60-day run -> 60 rows, not 240), idempotent
  on rerun (no duplicates), raises for a nonexistent run,
  `get_stored_analysis` returns `None`/raises the correct typed error
  for absent history / an invalid day / a nonexistent run, defaults to
  the latest persisted day, round-trips numerically IDENTICAL to a live
  `analyze_run()` call for the same day (current value, trend, rate,
  persistence, ICAR deviation, crop stages, agronomic context,
  data-quality notes all compared field-by-field), day 100's overlap
  survives the JSON round-trip, the module's own
  `python -m app.services.state_analysis.history --run-id N` entrypoint
  persists a real run and fails cleanly for a nonexistent one, and
  structural guards that the module never imports simulator-internal
  modules/`simulation_internal_state` and never references
  `routes/simulator.py`/`simulator_cli.py`/`create_run(` (Workflow A
  is a standalone entrypoint, not a duplicate creation path).

---

## 9. Decision log

- **Simulator represents virtual sensors, strictly separated from
  decision logic.** Reason: allows development without physical
  hardware now, and real-sensor replacement later without rewriting
  KAVACH.
- **Observations will occur every 6 hours (4/day) once the simulator
  exists.** Reason: continuous-monitoring realism without making the
  hackathon simulation unmanageable. Decision frequency (when KAVACH
  actually evaluates/recommends) is explicitly separate from data
  frequency — not yet designed.
- **ICAR reference data is frozen.** Reason: scientific provenance and
  reproducibility; it's a reference baseline, not something later phases
  get to quietly adjust.
- **No Alembic / migration framework.** Reason: the DB is a build
  artifact fully reproducible from `data/seed/tomato_reference.csv` +
  `seed_agronomics.py`'s own source-of-truth lists — a full rebuild from
  those is simpler and more honest than incremental ALTERs, given the
  project's own stated preference against hand-typed DB rows.
  Consequence: any future schema change to `agronomic_parameters` (or
  any other Phase 1 table) requires the same delete-and-reseed process
  used in 1.5C, with a backup taken first.
- **`status="derived"` and `status="context_dependent"` are distinct from
  `"missing"`/`"source_needed"`.** Reason: "we haven't found a source
  yet" and "this can never be a single fixed fact" are different claims;
  collapsing them would lose information a future phase needs.
- **LLM/ML/RL are not currently required.** Reason: the problem is
  solvable with structured data, agronomic knowledge, and deterministic
  models; nothing has yet demonstrated a need for any of the three. Not
  ruled out forever — ruled out for lack of current justification.
- **The simulator's NORMAL-scenario irrigation is calibrated per-day
  from the ICAR trajectory itself, using the simulator's own simplified
  evap model, clamped to a physically reasonable bound — and explicitly
  allowed to track only approximately, never forced to match exactly.**
  Reason (user-specified, quoted verbatim in `calibration.py`): "NORMAL
  irrigation is calibrated to keep the simplified virtual soil-moisture
  trajectory close to the ICAR reference. This is a simulator
  calibration mechanism, not a real-world irrigation recommendation."
- **Soil-moisture noise is applied only to the reported value, never fed
  back into the running state.** Reason: moisture is an integrator: any
  noise fed back into it compounds into a random walk whose drift grows
  with the square root of run length, which for a 60+ day run produced
  seed-dependent multi-point drift that defeated the calibration
  requirement above. This was discovered empirically during Phase 2
  implementation, not anticipated in the Phase 2A design.
- **Irrigation-share bookkeeping charges each day's calibrated
  irrigation to the transitions *originating from* that day (3 landing
  same-day, 1 landing on the next day's hour-0), not to the transitions
  *arriving at* that day.** Reason: the calibration formula computes
  "how much irrigation moves day d's moisture toward day d+1's moisture"
  — charging it to arrivals-within-day-d instead front-loads the whole
  amount into day d's own readings, visibly wrong whenever ICAR shows a
  same-day-to-next-day jump (e.g. day 28→29's real +3-point rise). Also
  discovered empirically, not anticipated in the design phase.
- **Trend direction is classified by an OLS slope vs. its own standard
  error (STABILITY_K=2.0, ~95% two-sided significance), not a
  fixed/agronomic threshold.** Reason (user-approved, Phase 3): the
  "what counts as a real trend" question has no agronomic answer --
  it's a statistical question about whether a slope is distinguishable
  from noise given the window's own observed variance. Using the
  regression's own residual noise keeps the method valid for a future
  real-sensor feed with a different noise profile than the simulator's,
  without KAVACH ever needing to know what that profile is in advance.
- **Day 100's real crop-stage overlap (`kc_mid_stage` ends day 100,
  `kc_late_stage` starts day 100, per Sharma & Changade 2025's own
  table) is reported as BOTH stages, never resolved to one.** Reason
  (user-approved, Phase 3): inventing a tie-break rule would be
  fabricating agronomic knowledge the source itself doesn't specify.
- **Phase 3 analysis is calculated on demand; no new database tables.**
  Reason (user-approved, Phase 3, original design): the source data is
  already immutable and persisted; the calculation is a deterministic
  pure function of it, small enough to be cheap on every call, and this
  project's no-Alembic delete-and-reseed migration cost would be paid
  on every future tuning of the analysis method if it were persisted
  instead. **Superseded** (user-approved, still Phase 3): Phase 4 needs
  a whole run's history without replaying 120 regressions per lookup,
  so `state_analysis_history` was added -- see the two entries below.
- **Phase 3 persistence is split into WORKFLOW A (backend, automatic,
  writes `state_analysis_history`) and WORKFLOW B (the CLI, read-only,
  never computes or writes).** Reason (user-specified): the CLI is a
  demo/debug interface and must stay that way even as the backend
  pipeline gets more automated -- conflating "show me the analysis" with
  "build the analysis" would make the CLI's behavior depend on whether
  it happened to be the first thing that ran, which is exactly the kind
  of implicit coupling this project has avoided everywhere else
  (simulator vs. decision logic, ICAR data vs. simulator output, etc.).
- **Workflow A is triggered automatically from
  `app.services.simulator.run_service.create_run()`, the one function
  both `POST /api/simulator/runs` and `python -m app.simulator_cli`
  already funnel every successful run through -- not from an
  SQLAlchemy event listener or any other implicit/global hook.** Reason
  (user-specified): a single, visible, explicit function call at the
  end of an existing function is auditable in a code review the way a
  global commit hook firing on every session (including unrelated
  seeding) is not; this is a hackathon project and the smallest correct
  mechanism was preferred over infrastructure (no event listeners,
  queues, or background jobs were introduced). If Phase 3's persistence
  call raises, the exception propagates out of `create_run()`
  unmodified -- the caller sees a failure rather than a false "success"
  with missing history, even though the already-committed Phase 2 data
  is not rolled back (consistent with runs being immutable/append-only).
- **Demo observability is now a binding architectural principle for
  every future phase, not just Phase 3.** See the "Demo observability
  principle" callout under section 1. Reason (user-specified): the
  backend must never become a black box during development or a
  hackathon demo -- every phase from here on needs a terminal (or
  equivalent) path from input through the phase's own service to
  visible output, without duplicating that service's logic in the
  demonstration layer.

---

## 10. Known limitations (kept current, never hidden)

- Only tomato is supported.
- ICAR reference dataset covers Day 1-120 only.
- `soil_bulk_density_g_cm3` and the mature-stage `dli_target_mol_m2_day`
  have no credible source yet.
- `eto_reference_mm_day`, `crop_water_requirement_mm_day`,
  `soil_available_water_capacity_mm` are documented as computable but
  nothing computes them yet — no water-requirement service exists.
- `soil_texture`, `soil_field_capacity_pct`,
  `soil_permanent_wilting_point_pct`, `irrigation_efficiency_pct` have no
  configuration model to live in yet — no real KAVACH farm/polyhouse is
  configured.
- Several sourced values are open-field or general-greenhouse, not
  polyhouse-and-India-specific (temperature thresholds, humidity bounds,
  root-zone depth, soil pH) — usable as evidence, not a perfect
  contextual match; picking a final value to actually consume in later
  logic needs a deliberate, documented decision, not a silent default.
- `stress_conditions` thresholds are still all NULL — no stress
  detection exists yet, even though some of the underlying temperature
  values that could feed `heat_stress` are now sourced.
- No decision engine, no intervention model, no optimizer, no validator,
  no farmer-facing UI.
- No physical sensors connected; nothing beyond this repo's own tests has
  validated any of this against a real polyhouse.
- The simulator's causal model is a deliberately simplified
  MODEL ASSUMPTION set (documented in `constants.py`), not FAO-56/
  Penman-Monteith or any validated soil-water physics. It produces
  plausible, causally-consistent numbers, not scientifically validated
  ones.
- The simulator supports exactly one scenario per run (no combining
  heatwave + water_shortage in the same run) and is hard-capped at
  120-day duration (the ICAR-verified span) with no extrapolation.
- The simulator's irrigation is an abstract per-slot percentage, not
  tied to any real pump/zone/flow-rate model — that mapping is
  explicitly future work (per the original architecture doc's
  irrigation-system-model phase), not touched in Phase 2.
- `simulation_internal_state` (irrigation/evap/scenario-delta debug
  fields) has no API exposure yet — it exists for test/traceability
  purposes only, queried directly via the DB in tests.
- **Phase 3's agronomic context is only day-resolvable for the `water`
  domain (Kc values).** Temperature/humidity/DLI/soil thresholds in
  `agronomic_parameters` are linked to the DAF Qld phenological stages,
  which have no day mapping in the source data -- Phase 3 reports this
  honestly (an explicit "no day-resolvable agronomic context" note)
  rather than inventing a day mapping. Giving those thresholds a real
  day mapping (or sourcing new day-mapped thresholds) is future
  Phase 1/1.5C work, not something Phase 3 can or should manufacture.
- **Phase 3's trend regression uses the ENTIRE available history up to
  the analysis day**, not a fixed recent lookback window (deliberately,
  to avoid inventing a window-size constant). A genuine late-run regime
  change can therefore be diluted by a long, differently-behaved
  earlier history rather than dominating the reported trend -- a known,
  documented trade-off of using "all available evidence" over "an
  arbitrary recent slice."
- **Out-of-range data-quality flagging is restricted to
  `humidity_pct`/`soil_moisture_pct`** (0-100% is a mathematical
  certainty). Temperature and N/P/K have no universally-true physical
  bound, so Phase 3 does not flag them -- doing so would require
  choosing an agronomic threshold, which this phase does not do.
- Phase 3 has no persisted analysis records -- every CLI/API call
  recomputes from `sensor_observations` + `tomato_reference_profile` +
  `agronomic_parameters` directly; there is no caching layer yet (not
  needed at current data volumes -- see the decision log).

---

## 11. What's next: Phase 4 (not started)

**Purpose**: problem / stress detection. Phase 3 (complete) produces
state/trend/persistence/ICAR-deviation/crop-stage/agronomic-context
data per sensor variable, per run -- it deliberately does NOT decide
whether any of that constitutes a problem. Phase 4 is where thresholds
get applied to that state to actually classify water stress, heat
stress, humidity stress, nutrient imbalance, etc. -- consuming Phase 3's
`StateAnalysis` output (`app.services.state_analysis.service.analyze_run`)
as its input, not re-deriving trend/rate/persistence itself.

This section is a pointer, not an approved design — Phase 4's actual
approach needs its own proposal-and-approval cycle before
implementation, same as every phase through Phase 3 got. Do not assume
any specific detection/threshold representation is already decided.
Per the demo observability principle (section 1), Phase 4 must also
ship with its own terminal-visible demonstration interface calling its
own service, not duplicating Phase 4's logic in the CLI.

---

## 12. Change log

**Phase 0** — ICAR PDF ingested, extracted to verified CSV, seeded to
`tomato_reference_profile`, reference API built, Day 47/120 regression
tests added. Files added: `app/services/extract_reference.py`,
`app/services/seed_database.py`, `app/models/tomato_reference.py`,
`app/models/data_source.py`, `app/schemas/tomato_reference.py`,
`app/routes/reference.py`, `app/main.py`, `tests/test_extraction.py`,
`tests/test_database_and_api.py`. Tests: 0 -> 16.

**Phase 1** — Agronomic knowledge base built (sources, stages,
parameters, stress conditions), all 23 non-reference parameters seeded as
`missing`/`source_needed` placeholders (no values yet). Files added:
`app/models/agronomic_{source,parameter,status}.py`,
`app/models/crop_stage.py`, `app/models/stress_condition.py`,
`app/schemas/agronomics.py`, `app/routes/agronomics.py`,
`app/services/seed_agronomics.py`, `tests/test_agronomics.py`. Tests: 16
-> 31.

**Phase 1.5B** — Web-research audit of the 23 unresolved parameters
against credible sources; no DB/schema/code changes. File added:
`docs/agronomic_parameter_audit.md`. Tests: unchanged at 31.

**Phase 1.5C** — Schema extended (`value_min`, `value_max`, CHECK
constraint, 2 new status values); `seed_agronomics.py` rewritten with 11
sources, 9 stages, 40 parameters carrying real provenance;
`test_agronomics.py` rewritten for the new data shape; DB backed up then
fully rebuilt. Files modified: `app/models/agronomic_parameter.py`,
`app/models/agronomic_status.py`, `app/schemas/agronomics.py`,
`app/services/seed_agronomics.py`, `tests/test_agronomics.py`. DB
backup: `data/backups/kavach.db.phase1_5c_backup_20260824_014234`. Tests:
31 -> 37, all passing. Sources added: 10 (11 total with pre-existing
ICAR row).

**Phase 2A (design)** — Proposal-and-approval cycle for the virtual
sensor simulator: initial proposal, one revision round (soil N/P/K
included as real sensor observations instead of excluded; DLI renamed
to `daily_dli_mol_m2_day` and duplicated across a day's 4 rows instead
of NULL-on-3-slots; full MODEL ASSUMPTION constant catalogue with
units/ranges/configurability documented), one final requirement (the
NORMAL-scenario irrigation calibration mechanism, with its exact
required wording). No files touched during 2A — proposal/discussion
only.

**Phase 2 (implementation)** — Built the simulator per the approved 2A
design. New tables: `simulation_runs`, `sensor_observations`,
`simulation_internal_state`. New module:
`app/services/simulator/{constants,rng,baseline,causal_model,
calibration,scenarios,config,generator,run_service}.py`. New:
`app/models/{simulation_run,sensor_observation,
simulation_internal_state}.py`, `app/schemas/simulator.py`,
`app/routes/simulator.py`, `tests/test_simulator.py`. Modified:
`app/main.py` (router registered), `tests/conftest.py` (import
`app.main` early so all models register before any `create_all()`
call -- this was itself a bug found and fixed during implementation:
without it, simulator tables silently never got created when
`seeded_db` ran before anything had imported the simulator models),
`tests/test_agronomics.py` (structural guard test renamed/narrowed --
`simulator`/`irrigation`/`pump`/`zone` removed from the forbidden-name
list since Phase 2 legitimately adds a simulator). Two real bugs found
via manual smoke-testing and fixed before trusting the automated test
suite: day-1 temperature/humidity discontinuity, and irrigation-share
off-by-one-day bookkeeping (see section 4 for both). One further
correction after tests initially passed but a tolerance-based sanity
test failed: soil-moisture noise was compounding into a random walk
because it was being fed back into the running state -- fixed by
separating the true (noise-free) state from the reported (noisy) value.
Tests: 37 -> 60, all passing. Phase 0 Day 47/120 and PDF checksum
re-verified unchanged.

**Phase 2.1** — Added `backend/app/simulator_cli.py`, a terminal-only
front-end for the existing simulator service (no new generation logic).
New: `tests/test_simulator_cli.py`. Modified: `README.md` (CLI usage
section), `docs/PROJECT_STATE.md`. One real bug found and fixed:
Windows console codepage (cp1252) couldn't encode the ✓/✗/box-drawing
output characters, which would have crashed the CLI on the exact
platform it targets -- fixed by forcing UTF-8 on stdout/stderr at
startup. Tests: 60 -> 74 (corrected from a stale "68" -- the file
actually had 14 tests already; see section 8), all passing. Phase 0/1/2
untouched (verified: PDF checksum unchanged, existing tests still pass
unmodified in behavior).

**Phase 3** — Sensor history / state analysis, built to the
user-approved Phase 3 proposal. New module:
`app/services/state_analysis/{parameters,current_state,trend,
persistence,icar_deviation,crop_stage_context,service}.py`. New:
`app/schemas/state_analysis.py`, `app/routes/state_analysis.py`,
`app/state_analysis_cli.py`, `tests/test_state_analysis.py`,
`tests/test_state_analysis_cli.py`. Modified: `app/main.py` (router
registered), `docs/PROJECT_STATE.md`, `README.md`. No new database
tables (on-demand calculation, per the approved persistence decision).
No Phase 0/1/1.5C/2/2.1 file was modified -- verified: ICAR PDF
checksum unchanged, `tomato_reference_profile`/`agronomic_sources`/
`crop_stages`/`agronomic_parameters`/`stress_conditions` row counts
unchanged (120/1/11/9/40/5), no new tables in `sqlite_master`, and all
74 pre-existing tests still pass unmodified. Established the demo
observability principle (section 1) as binding for all future phases.
Corrected a stale test-count claim inherited from Phase 2.1 (section
8). Tests: 74 -> 122, all passing.

**Phase 3 (automatic pipeline integration)** — Persistence pivot: added
`state_analysis_history` (new table, one row per run-day, JSON-encoded
per-parameter/stage/context detail) and split Phase 3 into Workflow A
(backend, `app/services/state_analysis/history.py::persist_run_history`,
now called automatically from `app/services/simulator/run_service.py
::create_run` -- the ONE Phase 2 file touched, a two-line addition plus
a one-line `db.refresh()` fix, no generation-equation file touched) and
Workflow B (`app/state_analysis_cli.py`, rewired to read
`get_stored_analysis` instead of computing `analyze_run` itself). New:
`app/models/state_analysis_history.py`,
`tests/test_state_analysis_history.py`. Modified:
`app/services/simulator/run_service.py`, `app/services/state_analysis/
{__init__,history}.py`, `app/state_analysis_cli.py`,
`tests/test_state_analysis.py`, `tests/test_state_analysis_cli.py`,
`docs/PROJECT_STATE.md`, `README.md`. The `GET
/api/analysis/tomato/runs/{run_id}` API route was deliberately left
calculating on demand (unchanged) -- switching it to read stored history
too was out of this integration's scope, noted as an open question.
One real bug found and fixed: `persist_run_history`'s own internal
commit re-expired the `run` object `create_run` had just refreshed,
so callers reading `run`'s attributes after closing their own session
hit `DetachedInstanceError` -- caught by the test suite (10 failures),
fixed with one more `db.refresh(run)`. A second, presentation-only bug
was also found and fixed during live verification: the CLI's "stage
ranges overlap" note fired on every ordinary day (since `full_cycle`
always co-matches alongside one Kc stage), not just the genuine day-100
overlap -- fixed by excluding `full_cycle` from the overlap count, with
a regression test added. No Phase 0/1/1.5C/2.1 file was modified;
`run_service.py` is the sole approved Phase 2 exception. Verified live:
Simulation #553 (60 days, heatwave/severe, start day 22, duration 10,
seed 123) generated via the real `python -m app.simulator_cli` ->
240 `sensor_observations`, 60 `state_analysis_history` rows, zero
manual persistence commands run. Tests: 122 -> 140, all passing.

---

*If you are a future Claude Code session reading this before starting
Phase 4 (or any later phase): verify every claim in this document against
the actual repository and running test suite before trusting it. Update
this document again before declaring your phase done.*
