"""
Deviation of the current (latest-observation) sensor value from the
Phase 0 ICAR reference trajectory for the same day. Reuses
app.services.simulator.baseline.load_baseline -- the EXISTING Phase 0
reference loader -- rather than re-reading tomato_reference_profile
independently. Never extrapolates past the loaded reference range.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.simulator.baseline import BaselineDay


@dataclass(frozen=True)
class IcarDeviation:
    parameter: str
    current_value: float
    icar_value: float | None
    icar_day: int
    signed_difference: float | None
    absolute_difference: float | None
    unit_suffix: str
    note: str | None


def compute_icar_deviation(
    parameter: str,
    current_value: float,
    day: int,
    baseline_field: str,
    baseline: dict[int, BaselineDay],
    unit_suffix: str,
) -> IcarDeviation:
    baseline_day = baseline.get(day)
    if baseline_day is None:
        return IcarDeviation(
            parameter, current_value, None, day, None, None, unit_suffix,
            note=f"No ICAR reference exists for day {day} (reference covers day 1-120 only).",
        )

    icar_value = getattr(baseline_day, baseline_field)
    diff = current_value - icar_value
    return IcarDeviation(parameter, current_value, icar_value, day, diff, abs(diff), unit_suffix, note=None)
