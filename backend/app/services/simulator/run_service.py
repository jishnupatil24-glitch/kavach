from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.sensor_observation import SensorObservation
from app.models.simulation_internal_state import SimulationInternalState
from app.models.simulation_run import SimulationRun
from app.services.simulator.baseline import load_baseline
from app.services.simulator.config import SimulationConfig
from app.services.simulator.generator import generate
from app.services.decision_engine.history import persist_run_decisions
from app.services.state_analysis.history import persist_run_history
from app.services.stress_assessment.history import persist_run_assessments


def create_run(db: Session, config: SimulationConfig) -> SimulationRun:
    baseline = load_baseline(db)
    slots = generate(config, baseline)

    run = SimulationRun(
        crop="tomato",
        duration_days=config.duration_days,
        scenario=config.scenario,
        severity=config.severity,
        seed=config.seed,
        scenario_start_day=config.scenario_start_day,
        scenario_duration_days=config.scenario_duration_days,
    )
    db.add(run)
    db.flush()  # obtain run.id

    for slot in slots:
        db.add(
            SensorObservation(
                simulation_run_id=run.id,
                day=slot.day,
                hour=slot.hour,
                temperature_c=slot.temperature_c,
                humidity_pct=slot.humidity_pct,
                soil_moisture_pct=slot.soil_moisture_pct,
                daily_dli_mol_m2_day=slot.daily_dli_mol_m2_day,
                soil_n_mg_kg=slot.soil_n_mg_kg,
                soil_p_mg_kg=slot.soil_p_mg_kg,
                soil_k_mg_kg=slot.soil_k_mg_kg,
            )
        )
        db.add(
            SimulationInternalState(
                simulation_run_id=run.id,
                day=slot.day,
                hour=slot.hour,
                irrigation_input_pct=slot.irrigation_input_pct,
                evaporative_loss_pct=slot.evaporative_loss_pct,
                temperature_delta_from_scenario=slot.temperature_delta_from_scenario,
                humidity_delta_from_scenario=slot.humidity_delta_from_scenario,
            )
        )

    db.commit()
    db.refresh(run)

    # Phase 2's own data (this run + its sensor_observations) is fully
    # committed above before Phase 3 ever runs -- Phase 3 only ever
    # processes a run whose raw observations already exist and are
    # durable. If persist_run_history raises, that exception propagates
    # to the caller (API/CLI) unmodified: the already-committed Phase 2
    # data is NOT rolled back (simulation_runs are immutable/append-only
    # by this project's own convention -- "regenerate" means a new run,
    # never mutating or discarding an existing one), but the overall
    # create_run() call reports failure rather than silently leaving
    # Phase 3 history missing while claiming success.
    persist_run_history(db, run.id)

    # persist_run_history() commits internally on the same session,
    # which (SQLAlchemy's default expire_on_commit=True) re-expires
    # every object in this session, including `run` -- so without this
    # second refresh, `run` would be handed back to the caller already
    # expired, and any caller who reads one of its attributes AFTER
    # closing their own session would hit DetachedInstanceError. This
    # restores the same "fully loaded, safe to read after close"
    # guarantee create_run() already gave its callers before Phase 3
    # was wired in.
    db.refresh(run)

    # Phase 4 runs only after Phase 3's history for this run is fully
    # committed above -- it reads that already-durable data via
    # get_stored_analysis, never recomputing it. Same failure-safety
    # reasoning as the Phase 3 call: if persist_run_assessments raises,
    # the exception propagates to the caller unmodified. Neither the
    # already-committed Phase 2 sensor_observations nor Phase 3's
    # state_analysis_history are rolled back or altered by a Phase 4
    # failure -- both remain exactly as they were, durable and correct;
    # only the overall create_run() call reports failure, rather than
    # silently claiming Phase 4 history exists when it doesn't.
    persist_run_assessments(db, run.id)

    # Same re-expiration reasoning as above, one more time: Phase 4's
    # own internal commit re-expires `run` again.
    db.refresh(run)

    # Phase 5 runs only after Phase 4's history for this run is fully
    # committed above -- it reads that already-durable data via
    # get_stored_assessment, never recomputing it. Same failure-safety
    # reasoning as the Phase 3/4 calls: if persist_run_decisions raises,
    # the exception propagates to the caller unmodified. None of the
    # already-committed Phase 2/3/4 data is rolled back or altered by a
    # Phase 5 failure.
    persist_run_decisions(db, run.id)

    # Same re-expiration reasoning as above: Phase 5's own internal
    # commit re-expires `run` again.
    db.refresh(run)

    return run
