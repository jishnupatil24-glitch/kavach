# KAVACH — Backend Architecture

## Repository layout (verified)

```
backend/
├── kavach.db                       SQLite DB, build artifact -- frontend must NOT open this file
├── requirements.txt, pytest.ini
├── app/
│   ├── main.py                     FastAPI app, registers every router
│   ├── database/session.py         SQLAlchemy engine/session/Base -- plain create_all, no Alembic
│   ├── models/                     one SQLAlchemy model file per table
│   ├── schemas/                    one Pydantic schema file per phase (XOut for responses, XCreate/XIn for request bodies)
│   ├── routes/                     one FastAPI router per phase
│   ├── services/
│   │   ├── seed_agronomics.py      Phase 1
│   │   ├── simulator/              Phase 2
│   │   ├── state_analysis/         Phase 3
│   │   ├── stress_assessment/      Phase 4
│   │   ├── decision_engine/        Phase 5
│   │   └── optimization/           Phase 6
│   ├── simulator_cli.py            Phase 2 terminal front-end
│   ├── state_analysis_cli.py       Phase 3 terminal front-end
│   ├── stress_assessment_cli.py    Phase 4 terminal front-end
│   ├── decision_cli.py             Phase 5 terminal front-end
│   └── optimization_cli.py         Phase 6 terminal front-end (read-only)
└── tests/
```

No `frontend/` directory exists yet. This handoff package is what a frontend project should be built against.

## Data flow (verified against actual service imports, not assumed)

```
Simulator (Phase 2)
      |  writes sensor_observations
      v
State Analysis (Phase 3)      reads sensor_observations + tomato_reference_profile + crop_stages/agronomic_parameters
      |  writes state_analysis_history
      v
Problem Assessment (Phase 4)  reads ONLY state_analysis_history (via get_stored_analysis)
      |  writes problem_assessment_history
      v
Decision Engine (Phase 5)     reads ONLY problem_assessment_history (via get_stored_assessment)
      |  writes decision_history
      v
Optimization (Phase 6)        reads ONLY decision_history (via get_stored_decision) + farm_configurations
      |  writes optimization_history
      v
Recommendation Validation (Phase 7)   -- NOT STARTED, no consumer exists yet
      |
Frontend (Phase 8)             -- calls the REST API layer only, never the DB
```

## Layer rules (enforced by structural tests in every phase's test file, not just convention)

- Each phase's service package may read **only** the immediately-preceding phase's own *stored* output (via that phase's `get_stored_X` function), never raw sensor data, never an earlier phase's live compute function, never an earlier phase's internal calculation modules directly.
- Every phase's CLI is presentation-only: it calls the phase's own `get_stored_X` (Workflow B) and never recomputes anything itself. A structural test scans each CLI's source for forbidden calculation-logic fragments and fails if any are found.
- No LLM/ML/RL exists anywhere in this codebase (Phase 5's eligibility gate and Phase 6's optimization are both deterministic rule-based code, verified by a structural guard test banning that vocabulary from the relevant modules).

## Workflow A / Workflow B (present in every phase from Phase 3 onward)

- **Workflow A** — backend processing: a `persist_run_X(db, run_id)` function that computes and stores one row per day for an entire run, called automatically once at the end of `app.services.simulator.run_service.create_run()` (the single function both `POST /api/simulator/runs` and `python -m app.simulator_cli` funnel every run through). Each phase's Workflow A call happens strictly after the previous phase's own Workflow A call in that same function, in this order: Phase 3 → Phase 4 → Phase 5 → Phase 6. Each is also independently runnable as a manual backfill: `python -m app.services.<phase>.history --run-id N`.
- **Workflow B** — presentation: the phase's CLI, which calls only `get_stored_X(db, run_id, day)` (the read path of the same `history.py` module) and never computes anything. If nothing is persisted yet for a run/day, the CLI names the Workflow A backfill command and exits, rather than computing a fallback.
- **Persistence shape**: one row per `(simulation_run_id, day)`, unique-constrained, idempotent (delete-then-reinsert on rerun). The per-day detail is a JSON blob (`dataclasses.asdict(...)` via `json.dumps`, stored in a `Text` column — not a native JSON column type), so the whole day's structured result round-trips exactly.

## Phase 6 specifically: what it may and may not do

**Consumes only** `app.services.decision_engine.history.get_stored_decision(db, run_id, day)` for its Phase 5 input, and `app.services.optimization.farm_config.get_farm_configuration(db, run_id)` for farm-specific input (a Phase-6-owned table, not upstream data).

**Must not, and does not** (verified by a structural test scanning `app/services/optimization/service.py` and `history.py` source): import or call Phase 5's `decide_run` (live compute), Phase 4's `assess_run`, Phase 3's `analyze_run`/`trend`/`persistence`/`icar_deviation` modules, or read `sensor_observations` directly.

**API route behavior**: `GET /api/optimization/tomato/runs/{run_id}` computes Phase 6's own result **on demand** (calling `optimize_run`, which itself only reads Phase 5's stored decision — this is not a Phase 3/4/5 recompute). This mirrors the existing convention: Phase 4 and Phase 5's own `GET` routes also compute on demand from their respective upstream stored history, while their CLIs read a separately-persisted history table. This was a deliberate, repeated architectural choice in this project, not an inconsistency.

## Database access rule for the frontend

**The frontend must never open `backend/kavach.db` directly.** Every value a frontend needs is already exposed through the REST API layer documented in `docs/API_CONTRACT.md`. If a needed value is not exposed by any existing endpoint, that is a backend gap to raise with the backend developer — not a reason to read the SQLite file from the frontend.
