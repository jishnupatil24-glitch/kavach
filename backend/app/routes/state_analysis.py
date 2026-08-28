from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.state_analysis import StateAnalysisOut
from app.services.state_analysis.service import InvalidDayError, RunNotFoundError, analyze_run

router = APIRouter(prefix="/api/analysis/tomato", tags=["tomato-state-analysis"])


@router.get("/runs/{run_id}", response_model=StateAnalysisOut)
def get_state_analysis(run_id: int, day: int | None = None, db: Session = Depends(get_db)):
    try:
        return analyze_run(db, run_id, day=day)
    except RunNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidDayError as e:
        raise HTTPException(status_code=422, detail=str(e))
