"""
Trend classification: an ordinary-least-squares (OLS) linear regression
of a sensor variable against elapsed time in days, not against
observation index -- this is what makes the fitted slope directly a
per-day rate regardless of gaps in the underlying data.

The caller (app.services.state_analysis.service.analyze_run) feeds
this module exactly ONE point per calendar day -- the day's daily
aggregate from daily_aggregation.py, never the day's individual 6-hour
readings -- so a day's own within-day noise can never be mistaken for
a multi-day trend. This module itself is agnostic to that: it fits
whatever (elapsed_time, value) pairs it is given, which also keeps it
usable against irregular future real-sensor timestamps, not just a
fixed daily grid.

Direction is classified by comparing the fitted slope against a
stability band derived from the regression's OWN residual noise -- a
standard statistical significance test (slope vs. its standard error),
never an externally chosen agronomic threshold. See STABILITY_K below
for the exact number and why it was picked.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

MIN_OBSERVATIONS_FOR_TREND = 3
"""
OLS residual variance needs n-2 >= 1 degrees of freedom to exist at
all: with exactly 2 points the fitted line passes through both exactly
(zero residual), which would make ANY nonzero slope look infinitely
significant against zero measured noise. 3 is the smallest n for which
the significance test below is meaningful at all.
"""

STABILITY_K = 2.0
"""
ANALYTICAL CONSTANT -- a statistical significance multiplier, not an
agronomic fact. Under the standard OLS assumption that residuals are
approximately normally distributed, slope +/- 2*SE(slope) is
approximately a 95% confidence interval for the true slope. A fitted
slope is only classified RISING/FALLING if it clears this band, i.e.
it is statistically distinguishable from "no trend" given THIS
window's own observed noise level -- not because it exceeds any
externally chosen number.
"""


@dataclass(frozen=True)
class TrendResult:
    parameter: str
    direction: str  # "RISING" | "FALLING" | "STABLE" | "UNDETERMINED"
    rate_per_day: float | None
    rate_unit: str
    standard_error_per_day: float | None
    stable_band: float | None  # +/- band, same units as rate_per_day
    n_observations: int
    note: str | None


def compute_trend(parameter: str, points: list[tuple[float, float]], rate_unit: str) -> TrendResult:
    """
    points: (elapsed_days, value) pairs, already filtered to the
    analysis window. Order does not matter -- sorted internally by
    elapsed_days is not required since OLS is order-independent.
    """
    n = len(points)
    if n < MIN_OBSERVATIONS_FOR_TREND:
        return TrendResult(
            parameter, "UNDETERMINED", None, rate_unit, None, None, n,
            note=(
                f"Only {n} observation(s) available -- at least "
                f"{MIN_OBSERVATIONS_FOR_TREND} are required to assess a trend."
            ),
        )

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n
    sxx = sum((x - x_mean) ** 2 for x in xs)
    sxy = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))

    if sxx == 0:
        return TrendResult(
            parameter, "UNDETERMINED", None, rate_unit, None, None, n,
            note="All observations in this window share the same elapsed time -- cannot fit a trend.",
        )

    slope = sxy / sxx
    intercept = y_mean - slope * x_mean
    residual_sum_sq = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(xs, ys))
    residual_variance = residual_sum_sq / (n - 2)
    standard_error = math.sqrt(residual_variance / sxx)
    stable_band = STABILITY_K * standard_error

    if slope > stable_band:
        direction = "RISING"
    elif slope < -stable_band:
        direction = "FALLING"
    else:
        direction = "STABLE"

    return TrendResult(parameter, direction, slope, rate_unit, standard_error, stable_band, n, note=None)
