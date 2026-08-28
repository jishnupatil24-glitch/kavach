"""
The simplified causal model tying temperature, humidity, and
evaporative soil-moisture loss together, so variables never move
independently/randomly of each other.

This is explicitly NOT a FAO-56 / Penman-Monteith soil-water model --
it is a lightweight simulator-only approximation. Every constant used
here is documented as a MODEL ASSUMPTION in constants.py.
"""
from __future__ import annotations

from app.services.simulator import constants as C

HOURS = (0, 6, 12, 18)

# MODEL ASSUMPTION: simple 4-point diurnal shape (trough at midnight,
# rising through dawn, peak at noon, falling through evening) rather
# than a sinusoid -- deliberately simple, not claiming a physical model
# of solar heating. Expressed as a fraction of the configured amplitude.
_DIURNAL_SHAPE = {0: -1.0, 6: -0.5, 12: 1.0, 18: 0.5}


def diurnal_temperature_offset(hour: int, amplitude_c: float = C.DIURNAL_TEMPERATURE_AMPLITUDE_C) -> float:
    return _DIURNAL_SHAPE[hour] * amplitude_c


def humidity_from_temperature_deviation(
    baseline_humidity_pct: float,
    temperature_deviation_c: float,
    coupling: float = C.TEMP_HUMIDITY_COUPLING_COEFFICIENT,
) -> float:
    """Hotter than the day's baseline -> somewhat lower relative humidity."""
    return baseline_humidity_pct - coupling * temperature_deviation_c


def evaporative_loss_pct(
    temperature_c: float,
    humidity_pct: float,
    base_rate: float = C.EVAP_BASE_RATE_PCT_PER_6H,
    temp_sensitivity: float = C.EVAP_TEMP_SENSITIVITY_PCT_PER_6H_PER_C,
    humidity_sensitivity: float = C.EVAP_HUMIDITY_SENSITIVITY_PCT_PER_6H_PER_PCT,
) -> float:
    """Simplified per-6-hour-slot soil-moisture loss. Never negative."""
    loss = (
        base_rate
        + temp_sensitivity * (temperature_c - 20.0)
        - humidity_sensitivity * (humidity_pct - 60.0)
    )
    return max(0.0, min(C.EVAP_MAX_PCT_PER_6H, loss))


def clamp(value: float, floor: float, ceiling: float) -> float:
    return max(floor, min(ceiling, value))
