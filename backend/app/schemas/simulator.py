from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

Scenario = Literal["normal", "heatwave", "water_shortage", "excess_irrigation", "high_humidity"]
Severity = Literal["mild", "moderate", "severe"]


class SimulationRunCreate(BaseModel):
    duration_days: int
    scenario: Scenario
    seed: int
    severity: Severity | None = None
    scenario_start_day: int | None = None
    scenario_duration_days: int | None = None

    @model_validator(mode="after")
    def _check_scenario_fields(self) -> "SimulationRunCreate":
        if self.scenario == "normal":
            if self.severity is not None:
                raise ValueError("severity must be null when scenario is 'normal'")
            if self.scenario_start_day is not None or self.scenario_duration_days is not None:
                raise ValueError(
                    "scenario_start_day/scenario_duration_days must be null when scenario is 'normal'"
                )
        else:
            if self.severity is None:
                raise ValueError(f"severity is required for scenario {self.scenario!r}")
            if self.scenario_start_day is None or self.scenario_duration_days is None:
                raise ValueError(
                    "scenario_start_day and scenario_duration_days are required "
                    f"for scenario {self.scenario!r}"
                )
        return self


class SimulationRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    crop: str
    duration_days: int
    scenario: str
    severity: str | None
    seed: int
    scenario_start_day: int | None
    scenario_duration_days: int | None
    created_at: datetime


class SensorObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    simulation_run_id: int
    day: int
    hour: int
    temperature_c: float
    humidity_pct: float
    soil_moisture_pct: float
    daily_dli_mol_m2_day: float
    soil_n_mg_kg: float
    soil_p_mg_kg: float
    soil_k_mg_kg: float
