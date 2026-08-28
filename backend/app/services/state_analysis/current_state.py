"""
Current state = the day's derived DAILY value (see
daily_aggregation.py) for the latest day present in the analysis
window -- never a single arbitrary 6-hour reading. This module exists
so every caller (trend/persistence/ICAR/CLI/API) uses the exact same
definition of "now": the LATEST DAY's daily-aggregated state.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.state_analysis.daily_aggregation import DailyValue
from app.services.state_analysis.parameters import ParameterSpec


@dataclass(frozen=True)
class CurrentState:
    parameter: str
    field: str
    value: float
    day: int
    n_readings: int
    note: str | None


def compute_current_state(daily_values: list[DailyValue], spec: ParameterSpec) -> CurrentState:
    """
    `daily_values` must already be filtered to the analysis window and
    sorted by day ascending (aggregate_daily's own contract) -- the
    last element is the latest day's daily state.
    """
    latest = daily_values[-1]
    return CurrentState(
        parameter=spec.label,
        field=spec.field,
        value=latest.value,
        day=latest.day,
        n_readings=latest.n_readings,
        note=latest.note,
    )
