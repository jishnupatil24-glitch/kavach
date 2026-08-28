from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.stress_assessment import StressAssessmentOut
from app.services.stress_assessment.service import InvalidDayError, RunNotFoundError, assess_run

router = APIRouter(prefix="/api/assessment/tomato", tags=["tomato-stress-assessment"])


@router.get("/runs/{run_id}", response_model=StressAssessmentOut)
def get_stress_assessment(run_id: int, day: int | None = None, db: Session = Depends(get_db)):
    try:
        return assess_run(db, run_id, day=day)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidDayError as e:
        raise HTTPException(status_code=422, detail=str(e))
