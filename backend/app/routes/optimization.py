from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.optimization import FarmConfigurationIn, FarmConfigurationOut, OptimizationAssessmentOut
from app.services.optimization.farm_config import RunNotFoundError as FarmConfigRunNotFoundError
from app.services.optimization.farm_config import upsert_farm_configuration
from app.services.optimization.service import InvalidDayError, RunNotFoundError, optimize_run
from app.services.optimization.units import UnsupportedAreaUnitError

router = APIRouter(prefix="/api/optimization/tomato", tags=["tomato-optimization"])


@router.get("/runs/{run_id}", response_model=OptimizationAssessmentOut)
def get_optimization(run_id: int, day: int | None = None, db: Session = Depends(get_db)):
    try:
        return optimize_run(db, run_id, day=day)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidDayError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/runs/{run_id}/farm-config", response_model=FarmConfigurationOut)
def set_farm_config(run_id: int, body: FarmConfigurationIn, db: Session = Depends(get_db)):
    try:
        return upsert_farm_configuration(db, run_id, **body.model_dump())
    except FarmConfigRunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UnsupportedAreaUnitError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except (ValueError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
