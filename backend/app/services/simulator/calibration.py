"""
NORMAL-scenario irrigation calibration.

MODEL ASSUMPTION:
"NORMAL irrigation is calibrated to keep the simplified virtual
soil-moisture trajectory close to the ICAR reference. This is a
simulator calibration mechanism, not a real-world irrigation
recommendation."

Method, per approved Phase 2A requirement, for each ICAR day d (1..120):
  1. Start from the ICAR reference soil moisture for day d.
  2. Using the simplified evaporative-loss model (causal_model.py)
     applied to that day's NOISELESS normal diurnal temperature/
     humidity curve, compute the total evaporative loss over the day's
     4 slots.
  3. Solve for the total daily irrigation input that would move the
     day's moisture from ICAR day d's value to (approximately) ICAR day
     d+1's value, given that evaporative loss:
         irrigation_needed = icar_moisture(d+1) - icar_moisture(d) + total_evap(d)
  4. Clamp irrigation_needed to [0, MAX_DAILY_IRRIGATION_PCT] -- a
     physically reasonable bound. When the ICAR trajectory would imply
     a value outside this bound (e.g. a decline steeper than the evap
     model alone explains, which would require "negative irrigation"),
     the result is clamped and the day is allowed to track ICAR only
     APPROXIMATELY rather than being forced to match exactly. This is
     deliberate -- see requirement point 4: never reverse-engineer an
     arbitrary irrigation value just to force an exact match.

This calibration table is computed ONCE per baseline (seed-independent,
deterministic), then reused as the irrigation baseline for every
scenario. Scenario disturbances (water_shortage, excess_irrigation)
multiply this calibrated baseline; heatwave/high_humidity leave it
unmodified and act through temperature/humidity instead (see
scenarios.py) -- which is what makes "moisture declines faster in a
heatwave, at an unchanged irrigation rate" a true causal statement
rather than a scripted override.

The calibration is NOT applied as a nightly hard-reset of simulated
moisture during actual generation -- doing so would erase multi-day
scenario effects (a water-shortage run would "heal" every midnight).
It is only the METHOD used to derive each day's calibrated_irrigation
value; the generator (generator.py) then runs soil moisture as one
continuous state across the whole simulation, anchored to the real
ICAR value only once, at day 1 / hour 0.
"""
from __future__ import annotations

from app.services.simulator import causal_model as CM
from app.services.simulator import constants as C
from app.services.simulator.baseline import BaselineDay


def build_calibrated_irrigation_table(baseline: dict[int, BaselineDay]) -> dict[int, float]:
    """Returns {day: calibrated_daily_irrigation_pct} for every day present in `baseline`."""
    table: dict[int, float] = {}
    max_day = max(baseline)

    for day, today in baseline.items():
        total_evap = 0.0
        for hour in CM.HOURS:
            temp = today.temperature_c + CM.diurnal_temperature_offset(hour)
            humidity = CM.humidity_from_temperature_deviation(
                today.humidity_pct, temp - today.temperature_c
            )
            humidity = CM.clamp(humidity, C.HUMIDITY_FLOOR_PCT, C.HUMIDITY_CEILING_PCT)
            total_evap += CM.evaporative_loss_pct(temp, humidity)

        if day < max_day and (day + 1) in baseline:
            target_delta = baseline[day + 1].soil_moisture_pct - today.soil_moisture_pct
        else:
            # Edge case: last day in the baseline has no ICAR day+1 to
            # target. Hold flat -- irrigation exactly offsets evap loss.
            target_delta = 0.0

        irrigation_needed = target_delta + total_evap
        table[day] = CM.clamp(irrigation_needed, 0.0, C.MAX_DAILY_IRRIGATION_PCT)

    return table
