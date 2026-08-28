from pydantic import BaseModel, ConfigDict


class RawRangeNoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    min_value: float
    max_value: float
    n_readings: int
    label: str


class SeverityFactorsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    deviation_ratio: float
    deviation_score: int
    intensity_ratio: float | None
    intensity_score: int
    duration_fraction: float
    duration_score: int
    total_score: int


class AbnormalStateDurationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    tier: str  # sourced_threshold | icar_sign_trend_proxy
    days: int | None
    provenance_note: str


class ProblemAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    category: str
    label: str
    field: str
    status: str
    direction: str
    current_value: float
    icar_value: float | None
    icar_deviation: float | None
    rate_per_day: float | None
    rate_unit: str
    persistence_days: int | None
    sourced_corroboration_notes: list[str]
    provenance_notes: list[str]
    raw_range: RawRangeNoteOut | None
    # Severity is INDEPENDENT of `status` above -- see severity_disclaimer.
    severity: str
    severity_factors: SeverityFactorsOut | None
    severity_disclaimer: str
    # SEPARATE from persistence_days above -- see AbnormalStateDurationOut.
    abnormal_state_duration: AbnormalStateDurationOut


class StageMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage_id: int
    name: str
    start_day: int
    end_day: int
    source_id: int | None


class StressAssessmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    crop: str
    assessment_day: int
    problems: list[ProblemAssessmentOut]
    crop_stages: list[StageMatchOut]
