"""
Derives ONE representative value per day from Phase 2's four 6-hour
sensor_observations rows, WITHOUT deleting, modifying, or collapsing
those raw rows -- sensor_observations remains the untouched source of
truth (Phase 2, 4 rows/day); this module only reads it.

Point-in-time variables (temperature, humidity, soil moisture, soil
N/P/K) are averaged: the arithmetic mean of whatever readings are
actually available that day (never assumed to be exactly 4 -- a
missing slot just means a smaller denominator; the general "day has
fewer than 4 readings" fact is already reported by
service._data_quality_notes, so this module does not duplicate that
note for these fields).

DLI (daily_dli_mol_m2_day) is NOT averaged. Phase 2 stores the same
daily-integral figure duplicated across a day's 4 rows by design (see
app/models/sensor_observation.py's own docstring) -- averaging four
copies of one number is meaningless arithmetic and would silently mask
a real disagreement if the duplicates ever differed. Instead, one of
the available readings is used as the day's value, and any
disagreement across the day's rows is reported as an explicit
data-quality note, never averaged away.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.models.sensor_observation import SensorObservation

DAILY_INTEGRAL_FIELDS = {"daily_dli_mol_m2_day"}


@dataclass(frozen=True)
class DailyValue:
    day: int
    value: float
    n_readings: int
    note: str | None


def aggregate_daily(observations: list[SensorObservation], field: str) -> list[DailyValue]:
    """
    observations: any SensorObservation rows (any day range, any
    number of slots per day), NOT required to be pre-sorted. Grouped
    here by `.day`. Returns one DailyValue per distinct day that has at
    least one non-null reading for `field`, sorted by day ascending. A
    day with zero readings for this field simply does not appear here
    (today's schema makes that impossible -- every column is
    non-nullable -- but a future nullable real-sensor field could
    produce it; the caller sees a day missing from this list exactly
    like any other missing-data case).
    """
    by_day: dict[int, list[float]] = {}
    for o in observations:
        value = getattr(o, field)
        if value is not None:
            by_day.setdefault(o.day, []).append(value)

    results: list[DailyValue] = []
    for day in sorted(by_day):
        values = by_day[day]
        n = len(values)

        if field in DAILY_INTEGRAL_FIELDS:
            distinct = sorted(set(values))
            note = None
            if len(distinct) > 1:
                note = (
                    f"Day {day}: the {n} available {field} readings disagree "
                    f"({distinct}) -- expected one daily-integral value "
                    "duplicated across the day's slots; using the first "
                    "available reading rather than averaging them."
                )
            results.append(DailyValue(day=day, value=values[0], n_readings=n, note=note))
        else:
            results.append(DailyValue(day=day, value=sum(values) / n, n_readings=n, note=None))

    return results
