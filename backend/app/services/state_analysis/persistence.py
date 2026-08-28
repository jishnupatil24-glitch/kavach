"""
Trend persistence: how many consecutive days (walking backward from the
most recent day with data) the day-level MEAN has kept moving
consistently with the direction reported by trend.py. Day-level
averaging (not raw 6-hour readings) is used specifically so an
individual 6-hour noise reading can never flip the count on its own --
averaging up to 4 readings/day already reduces that noise before this
check runs at all.

Reuses trend.py's own `stable_band` (already expressed in per-day
units) as the day-over-day step threshold, instead of inventing a
second, separate constant.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersistenceResult:
    parameter: str
    direction: str
    days: int | None
    note: str | None


def _day_means(points: list[tuple[int, float]]) -> list[tuple[int, float]]:
    by_day: dict[int, list[float]] = {}
    for day, value in points:
        by_day.setdefault(day, []).append(value)
    return sorted((day, sum(values) / len(values)) for day, values in by_day.items())


def compute_persistence(
    parameter: str,
    points: list[tuple[int, float]],
    direction: str,
    stable_band: float | None,
) -> PersistenceResult:
    if direction == "UNDETERMINED" or stable_band is None:
        return PersistenceResult(parameter, direction, None, "Trend is undetermined -- persistence cannot be assessed.")

    means = _day_means(points)
    if len(means) < 2:
        return PersistenceResult(
            parameter, direction, None,
            f"Only {len(means)} day(s) of data -- at least 2 are required to assess persistence.",
        )

    streak = 1  # the latest day itself always counts
    for i in range(len(means) - 1, 0, -1):
        delta = means[i][1] - means[i - 1][1]
        if direction == "RISING" and delta > stable_band:
            streak += 1
        elif direction == "FALLING" and delta < -stable_band:
            streak += 1
        elif direction == "STABLE" and abs(delta) <= stable_band:
            streak += 1
        else:
            break

    return PersistenceResult(parameter, direction, streak, None)
