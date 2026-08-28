from pydantic import BaseModel, ConfigDict


class CurrentStateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter: str
    field: str
    value: float
    day: int
    n_readings: int
    note: str | None


class TrendOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter: str
    direction: str
    rate_per_day: float | None
    rate_unit: str
    standard_error_per_day: float | None
    stable_band: float | None
    n_observations: int
    note: str | None


class PersistenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter: str
    direction: str
    days: int | None
    note: str | None


class IcarDeviationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter: str
    current_value: float
    icar_value: float | None
    icar_day: int
    signed_difference: float | None
    absolute_difference: float | None
    unit_suffix: str
    note: str | None


class ParameterAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current: CurrentStateOut
    trend: TrendOut
    persistence: PersistenceOut
    icar: IcarDeviationOut


class StageMatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stage_id: int
    name: str
    start_day: int
    end_day: int
    source_id: int | None


class AgronomicContextItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    parameter_name: str
    domain: str
    value_display: str
    unit: str | None
    status: str
    source_id: int | None
    context: str | None
    notes: str | None


class StateAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: int
    crop: str
    analysis_day: int
    duration_days: int
    parameters: list[ParameterAnalysisOut]
    crop_stages: list[StageMatchOut]
    agronomic_context: list[AgronomicContextItemOut]
    data_quality_notes: list[str]
