from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.sensor_observation import SensorObservation
from app.models.simulation_run import SimulationRun
from app.schemas.simulator import SensorObservationOut, SimulationRunCreate, SimulationRunOut
from app.services.simulator.config import SimulationConfigError, build_config
from app.services.simulator.run_service import create_run

router = APIRouter(prefix="/api/simulator", tags=["simulator"])


@router.post("/runs", response_model=SimulationRunOut, status_code=201)
def create_simulation_run(payload: SimulationRunCreate, db: Session = Depends(get_db)):
    try:
        config = build_config(
            duration_days=payload.duration_days,
            scenario=payload.scenario,
            seed=payload.seed,
            severity=payload.severity,
            scenario_start_day=payload.scenario_start_day,
            scenario_duration_days=payload.scenario_duration_days,
        )
    except SimulationConfigError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return create_run(db, config)


@router.get("/runs", response_model=list[SimulationRunOut])
def list_simulation_runs(db: Session = Depends(get_db)):
    return db.query(SimulationRun).order_by(SimulationRun.id).all()


@router.get("/runs/{run_id}", response_model=SimulationRunOut)
def get_simulation_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"No simulation run found with id {run_id}")
    return run


@router.get("/runs/{run_id}/observations", response_model=list[SensorObservationOut])
def get_simulation_observations(run_id: int, day: int | None = None, db: Session = Depends(get_db)):
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise HTTPException(status_code=404, detail=f"No simulation run found with id {run_id}")

    query = db.query(SensorObservation).filter(SensorObservation.simulation_run_id == run_id)
    if day is not None:
        query = query.filter(SensorObservation.day == day)
    return query.order_by(SensorObservation.day, SensorObservation.hour).all()
