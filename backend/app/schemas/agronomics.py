from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.agronomic_status import AGRONOMIC_STATUS_VALUES

AgronomicStatus = Literal[
    "sourced", "assumption", "missing", "source_needed", "derived", "context_dependent",
    "project_defined",
]
assert set(AgronomicStatus.__args__) == set(AGRONOMIC_STATUS_VALUES)


class AgronomicSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_or_author: str | None
    title: str | None
    publication_year: int | None
    source_type: str | None
    document_reference: str | None
    description: str | None
    notes: str | None


class CropStageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop: str
    name: str
    start_day: int | None
    end_day: int | None
    description: str | None
    source_id: int | None
    notes: str | None


class AgronomicParameterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop: str
    domain: str
    parameter_name: str
    value_numeric: float | None
    value_min: float | None
    value_max: float | None
    value_text: str | None
    unit: str | None
    stage_id: int | None
    context: str | None
    status: AgronomicStatus
    source_id: int | None
    notes: str | None


class StressConditionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop: str
    stress_type: str
    affected_parameter: str
    operator: str
    threshold_value: float | None
    unit: str | None
    stage_id: int | None
    severity: str | None
    status: AgronomicStatus
    source_id: int | None
    description: str | None
    notes: str | None
