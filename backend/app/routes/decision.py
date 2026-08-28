from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.decision import DecisionAssessmentOut
from app.services.decision_engine.service import InvalidDayError, RunNotFoundError, decide_run

router = APIRouter(prefix="/api/decision/tomato", tags=["tomato-decision-engine"])


@router.get("/runs/{run_id}", response_model=DecisionAssessmentOut)
def get_decision(run_id: int, day: int | None = None, db: Session = Depends(get_db)):
    try:
        return decide_run(db, run_id, day=day)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidDayError as e:
        raise HTTPException(status_code=422, detail=str(e))
