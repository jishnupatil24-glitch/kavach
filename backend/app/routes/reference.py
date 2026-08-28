from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.tomato_reference import TomatoReferenceProfile
from app.schemas.tomato_reference import TomatoReferenceProfileOut

router = APIRouter(prefix="/api/reference/tomato", tags=["tomato-reference"])


@router.get("", response_model=list[TomatoReferenceProfileOut])
def list_tomato_reference(db: Session = Depends(get_db)):
    return (
        db.query(TomatoReferenceProfile)
        .order_by(TomatoReferenceProfile.day)
        .all()
    )


@router.get("/day/{day}", response_model=TomatoReferenceProfileOut)
def get_tomato_reference_day(day: int, db: Session = Depends(get_db)):
    record = (
        db.query(TomatoReferenceProfile)
        .filter(TomatoReferenceProfile.day == day)
        .first()
    )
    if record is None:
        raise HTTPException(
            status_code=404, detail=f"No reference record found for day {day}"
        )
    return record
