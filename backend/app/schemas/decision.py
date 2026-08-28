from pydantic import BaseModel, ConfigDict


class GateCheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    passed: bool | None
    detail: str


class DecisionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    label: str
    status: str
    severity: str
    abnormal_duration_days: int | None
    abnormal_duration_tier: str
    eligibility_checks: list[GateCheckOut]
    conflict_with: str | None
    outcome: str
    action_label: str | None
    action_type: str | None
    action_basis: str
    decision_provenance: str
    quantitative_basis: None
    limitations: list[str]
    priority: int | None
    priority_reason: str | None


class DecisionAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    crop: str
    assessment_day: int
    decisions: list[DecisionRecordOut]
