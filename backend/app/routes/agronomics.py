from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.agronomic_parameter import AgronomicParameter
from app.models.agronomic_source import AgronomicSource
from app.models.crop_stage import CropStage
from app.models.stress_condition import StressCondition
from app.schemas.agronomics import (
    AgronomicParameterOut,
    AgronomicSourceOut,
    CropStageOut,
    StressConditionOut,
)

router = APIRouter(prefix="/api/agronomics/tomato", tags=["tomato-agronomics"])


@router.get("/sources", response_model=list[AgronomicSourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(AgronomicSource).order_by(AgronomicSource.id).all()


@router.get("/stages", response_model=list[CropStageOut])
def list_stages(db: Session = Depends(get_db)):
    return (
        db.query(CropStage)
        .filter(CropStage.crop == "tomato")
        .order_by(CropStage.id)
        .all()
    )


@router.get("/stages/{stage_id}", response_model=CropStageOut)
def get_stage(stage_id: int, db: Session = Depends(get_db)):
    stage = db.query(CropStage).filter(CropStage.id == stage_id).first()
    if stage is None:
        raise HTTPException(status_code=404, detail=f"No stage found with id {stage_id}")
    return stage


@router.get("/parameters", response_model=list[AgronomicParameterOut])
def list_parameters(
    status: str | None = None,
    domain: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(AgronomicParameter).filter(AgronomicParameter.crop == "tomato")
    if status is not None:
        query = query.filter(AgronomicParameter.status == status)
    if domain is not None:
        query = query.filter(AgronomicParameter.domain == domain)
    return query.order_by(AgronomicParameter.id).all()


@router.get("/parameters/{parameter_name}", response_model=list[AgronomicParameterOut])
def get_parameter(parameter_name: str, db: Session = Depends(get_db)):
    records = (
        db.query(AgronomicParameter)
        .filter(
            AgronomicParameter.crop == "tomato",
            AgronomicParameter.parameter_name == parameter_name,
        )
        .order_by(AgronomicParameter.id)
        .all()
    )
    if not records:
        raise HTTPException(
            status_code=404, detail=f"No parameter found named '{parameter_name}'"
        )
    return records


@router.get("/stress-conditions", response_model=list[StressConditionOut])
def list_stress_conditions(db: Session = Depends(get_db)):
    return (
        db.query(StressCondition)
        .filter(StressCondition.crop == "tomato")
        .order_by(StressCondition.id)
        .all()
    )
