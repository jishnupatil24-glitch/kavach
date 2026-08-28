"""
Scenario disturbance functions layered on top of the causal model and
the NORMAL calibration baseline. Each scenario has exactly one internal
cause -- it never touches a variable it doesn't have a documented
mechanism for.

heatwave / high_humidity: external forcing (temperature / humidity),
    ramped in and out over 1 day each side of the plateau window --
    these represent gradual climate-like disturbances.
water_shortage / excess_irrigation: a control-input change (the
    calibrated irrigation rate is multiplied), applied as a sharp
    on/off window -- these represent a discrete change in irrigation
    schedule, which realistically can happen abruptly, so no ramp.
"""
from __future__ import annotations

from app.services.simulator import constants as C
from app.services.simulator.config import SimulationConfig


def _forcing_intensity_fraction(day: int, start: int, duration: int) -> float:
    """
    1.0 during the plateau, 0.5 on the ramp-in day (start) and the
    ramp-out day (start+duration, one day past the plateau), 0.0
    otherwise. MODEL ASSUMPTION: a simple 1-day linear-feeling ramp,
    not a physically derived onset/decay curve.
    """
    end_plateau = start + duration - 1
    ramp_out_day = start + duration
    if day == start:
        return 0.5
    if start < day <= end_plateau:
        return 1.0
    if day == ramp_out_day:
        return 0.5
    return 0.0


def temperature_delta_c(day: int, config: SimulationConfig) -> float:
    if config.scenario != "heatwave":
        return 0.0
    magnitude = C.HEATWAVE_TEMP_DELTA_C[config.severity]
    fraction = _forcing_intensity_fraction(day, config.scenario_start_day, config.scenario_duration_days)
    return magnitude * fraction


def humidity_delta_pct(day: int, config: SimulationConfig) -> float:
    if config.scenario != "high_humidity":
        return 0.0
    magnitude = C.HIGH_HUMIDITY_DELTA_PCT[config.severity]
    fraction = _forcing_intensity_fraction(day, config.scenario_start_day, config.scenario_duration_days)
    return magnitude * fraction


def irrigation_multiplier(day: int, config: SimulationConfig) -> float:
    if config.scenario == "water_shortage":
        start, duration = config.scenario_start_day, config.scenario_duration_days
        if start <= day <= start + duration - 1:
            return C.WATER_SHORTAGE_IRRIGATION_MULTIPLIER[config.severity]
        return 1.0
    if config.scenario == "excess_irrigation":
        start, duration = config.scenario_start_day, config.scenario_duration_days
        if start <= day <= start + duration - 1:
            return C.EXCESS_IRRIGATION_MULTIPLIER[config.severity]
        return 1.0
    return 1.0
