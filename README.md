# KAVACH

KAVACH is a sustainability-focused agricultural decision-support system for
tomato cultivation in a polyhouse (protected-cultivation) environment. Its
primary objective is water optimization: recommend the minimum irrigation
intervention needed to keep the crop in an acceptable state, including
recommending no intervention when none is needed.

This repository currently implements **Phase 0** (ICAR reference data
ingestion), **Phase 1** (agronomic knowledge base), **Phase 2** (virtual
sensor simulator), and **Phase 3** (sensor history / state analysis). No
stress/problem detection, irrigation logic, decision engine, or LLM
exists yet.

## The reference dataset

`data/sources/icar/tomato_reference.pdf` is the original ICAR-derived
tomato polyhouse dataset (Day 1-120), kept as-is for provenance and
traceability. It is **not** modified during extraction.

**This is a reference profile, not live sensor data.** It describes an
expected/baseline crop trajectory (environmental conditions, target soil
NPK concentrations, and modelled daily nutrient demand) for a tomato
polyhouse — it is not a "ground truth" label, not simulated sensor data,
and not a direct recommendation table.

`data/seed/tomato_reference.csv` is the structured, verified extraction of
that PDF's table, produced by
`backend/app/services/extract_reference.py`. Extraction performs no
estimation, interpolation, correction, or invention of values — it parses
exactly what the PDF table contains and validates structural expectations
(120 rows, days 1-120 with no gaps/duplicates, all values numeric).

The SQLite database (`backend/kavach.db`) is seeded from the CSV, not from
the PDF, by `backend/app/services/seed_database.py`. The pipeline is:

```
ICAR PDF -> extracted/verified CSV -> SQLite -> API
```

### Columns

| CSV/DB column              | Meaning                              |
|-----------------------------|---------------------------------------|
| `day`                       | Day number, 1-120                     |
| `soil_moisture_pct`         | Soil moisture (%)                     |
| `temperature_c`             | Temperature (°C)                      |
| `humidity_pct`              | Humidity (%)                          |
| `dli_mol_m2_day`            | Daily Light Integral (mol/m²/day)     |
| `soil_n_mg_kg`              | Soil nitrogen (mg/kg)                 |
| `soil_p_mg_kg`              | Soil phosphorus (mg/kg)               |
| `soil_k_mg_kg`              | Soil potassium (mg/kg)                |
| `n_demand_g_plant_day`      | N demand (g/plant/day)                |
| `p2o5_demand_g_plant_day`   | P₂O₅ demand (g/plant/day)             |
| `k2o_demand_g_plant_day`    | K₂O demand (g/plant/day)              |

Note: the source PDF's text layer has a font-encoding issue that corrupts
the degree symbol, superscript "²", and the "₂"/"₅" subscripts in column
headers. The underlying numeric data is unaffected; column names above
are resolved using standard agronomic notation, not guessed.

## The agronomic knowledge base (Phase 1)

The **ICAR reference profile** (`tomato_reference_profile`) is a Day 1-120
trajectory. The **agronomic knowledge base** is a separate, smaller set of
structured tables holding general/stage-specific agricultural knowledge
used to *interpret* that trajectory — the two are not the same thing and
are never merged.

| Table                   | Purpose                                                         |
|--------------------------|------------------------------------------------------------------|
| `agronomic_sources`      | Provenance for agronomic knowledge (title, type, document reference). Distinct from Phase 0's `data_source`. |
| `crop_stages`            | Named crop-cycle periods with day ranges, when sourced.          |
| `agronomic_parameters`   | Individual sourced-or-not parameters (Kc, temperature bounds, soil characteristics, nutrient totals, ...). |
| `stress_conditions`      | Knowledge-only representation of stress thresholds (water stress, heat stress, ...) — no diagnosis logic reads these yet. |

Every row in `agronomic_parameters` / `stress_conditions` carries a
`status`:

- **`sourced`** — a value directly supported by a documented source; always has a non-null `source_id` and a non-null value.
- **`assumption`** — a modelling assumption, explicitly not presented as scientific fact.
- **`missing`** — a parameter later phases may need, with no source identified yet.
- **`source_needed`** — a specific candidate value exists (e.g. surfaced in project discussion) but no verifiable source has been confirmed, so the value is withheld.

**What is actually sourced right now:** only the `full_cycle` crop stage
(Day 1-120), because that span is read directly from the already-verified
Phase 0 data, not from outside claims.

**What is withheld pending a source:** the Kc candidates for protected
cultivation (initial 0.53 / mid-season 1.08 / late-season 0.63) surfaced
during project discussion — no verifiable source document for them exists
in this repository, so they are stored as `kc_initial` / `kc_mid` /
`kc_late` with `status="source_needed"` and `value_numeric=None`, not as
facts. The same treatment applies to temperature bounds, humidity bounds,
DLI targets, soil-water characteristics (field capacity, wilting point,
bulk density, root-zone depth, texture, pH, EC), and total-season N/P₂O₅/K₂O
requirements — all `status="missing"`, all `value_numeric=None`.

Nutrient identity is kept explicit throughout: `soil_p_mg_kg` (elemental P)
is never treated as equal to `p2o5_demand_g_plant_day` or
`p2o5_total_requirement_g_plant_season` (P₂O₅), and likewise for K vs. K₂O.

Seed with:

```
cd backend
python -m app.services.seed_agronomics
```

## Setup

```
cd backend
python -m venv .venv
.venv/Scripts/activate        # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

## Re-running extraction and seeding the database

```
cd backend
python -m app.services.extract_reference   # PDF -> data/seed/tomato_reference.csv
python -m app.services.seed_database       # CSV -> backend/kavach.db
python -m app.services.seed_agronomics     # agronomic knowledge base -> backend/kavach.db
```

## Running tests

```
cd backend
pytest tests/ -v
```

## Running the API

```
cd backend
uvicorn app.main:app --reload
```

Then:

- `GET /health`
- `GET /api/reference/tomato` — full reference profile
- `GET /api/reference/tomato/day/{day}` — single day's reference record
  (404 if `day` is outside 1-120)
- `GET /api/agronomics/tomato/sources` — agronomic source/provenance records
- `GET /api/agronomics/tomato/stages` / `.../stages/{stage_id}` — crop stages
- `GET /api/agronomics/tomato/parameters` (optional `?status=` / `?domain=`) — agronomic parameters
- `GET /api/agronomics/tomato/parameters/{parameter_name}` — a parameter by name
- `GET /api/agronomics/tomato/stress-conditions` — stress-condition knowledge records
- `GET /api/analysis/tomato/runs/{run_id}` / `?day=D` — Phase 3 state analysis for a simulation run (see below)

These endpoints expose agricultural facts (and their sourcing status)
only — they make no recommendations or diagnoses.

### Virtual sensor simulator (Phase 2)

- `POST /api/simulator/runs` — generate a virtual-sensor observation
  history: `{duration_days (1-120), scenario, seed, severity, scenario_start_day, scenario_duration_days}`.
  `scenario` is one of `normal | heatwave | water_shortage | excess_irrigation | high_humidity`;
  `severity`/window fields are required for every scenario except `normal`.
- `GET /api/simulator/runs` / `GET /api/simulator/runs/{id}` — run metadata
- `GET /api/simulator/runs/{id}/observations` (optional `?day=`) — the generated 6-hour observations

The simulator generates plausible, causally-consistent virtual sensor
readings only — it does not diagnose problems, does not recommend
interventions, and is not the decision-making part of KAVACH. See
`docs/PROJECT_STATE.md` for the full design/architecture notes.

### Simulator CLI (Phase 2.1)

For running the simulator directly from a terminal (no API server, no
JSON) during a demo:

```
cd backend
python -m app.simulator_cli
```

This walks through duration/scenario/severity/seed prompts, generates a
real simulation via the existing simulator service, and prints a
polished summary: confirmation checklist, first/last day tables, and
temperature/soil-moisture summary stats.

To view a specific day of an existing simulation:

```
python -m app.simulator_cli --run-id 7 --day 35
```

The CLI is a thin terminal front-end only — it contains no simulation
logic of its own; it calls the same `app.services.simulator` code as the
HTTP API.

### Sensor history / state analysis (Phase 3)

Interprets an existing simulation run's `sensor_observations` over
time: current value, trend direction, rate of change, trend
persistence, deviation from the Phase 0 ICAR reference, applicable
Phase 1/1.5C crop stage, and any day-resolvable agronomic context —
for temperature, humidity, soil moisture, DLI, and soil N/P/K.

**This phase does not diagnose stress or recommend anything.** It
describes what the sensor history shows; deciding whether that
constitutes a problem is Phase 4's job.

- `GET /api/analysis/tomato/runs/{run_id}` — full state analysis as of
  the run's last day, calculated on demand
- `GET /api/analysis/tomato/runs/{run_id}?day=D` — state analysis using
  only the observation history up to and including day `D`

Trend direction (RISING / FALLING / STABLE) is decided by an ordinary
least-squares regression of each variable against elapsed time,
compared against a stability band derived from that regression's own
residual noise (`STABILITY_K = 2.0` standard errors — an analytical/
statistical significance threshold, not an agronomic one). See
`app/services/state_analysis/trend.py` for the exact formula.

**Phase 3 runs automatically.** As soon as a simulation is generated —
by `POST /api/simulator/runs` or `python -m app.simulator_cli` — Phase 3
computes and stores one daily state-analysis record per simulated day
in `state_analysis_history` (a 40-day simulation produces 160 raw
`sensor_observations` and 40 Phase 3 daily records — the raw
observations are never deleted, replaced, or averaged away; Phase 3's
history is a derived layer on top of them). No extra command is
needed.

This backend pipeline (Workflow A) and the terminal demo (Workflow B,
below) are deliberately separate: the CLI only ever *reads* what
Workflow A already stored — it never computes analysis itself and
never creates missing history, even when you pass `--day`.

Terminal demo, no API server needed:

```
cd backend
python -m app.state_analysis_cli --run-id 7
python -m app.state_analysis_cli --run-id 7 --day 35
```

The CLI is presentation-only — it calls
`app.services.state_analysis.history.get_stored_analysis`, reading the
same `state_analysis_history` rows Workflow A wrote; it never
duplicates the analysis logic. If a run somehow has no stored history
yet (e.g. one created before this automatic pipeline existed), the CLI
says so and names the manual backfill command instead of computing a
fallback:

```
python -m app.services.state_analysis.history --run-id 7
```

`state_analysis_history` is the only new database table Phase 3 adds —
one row per `(simulation_run_id, day)` for the whole run, storing a
JSON-serialized copy of the same analysis `analyze_run` computes
on-demand elsewhere (the API route above still calculates on demand and
does not read this table).
