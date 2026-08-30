"""
Optional resource-constraint evaluation. Missing input NEVER becomes
PASS and never blocks the rest of the optimization -- it produces
NOT_EVALUATED, reported alongside PASS/FAIL, never coerced to either.
"""
from __future__ import annotations

from dataclasses import dataclass

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_NOT_EVALUATED = "NOT_EVALUATED"

HOURS_PER_DAY = 24
"""
No pump-operating-hours assumption was approved for Phase 6, so the
pump-capacity check uses this plain unit-conversion constant (not an
operational assumption) to get the pump's theoretical 24-hour maximum
output -- a conservative UPPER bound, not a realistic duty-cycle
estimate. Labelled as such in the detail text.
"""


@dataclass(frozen=True)
class FeasibilityCheck:
    label: str  # "available_water" | "pump_capacity"
    status: str  # PASS | FAIL | NOT_EVALUATED
    detail: str


_DEFAULT_VOLUME_UNAVAILABLE_REASON = (
    "Required delivered field volume is unavailable -- feasibility not evaluated."
)
"""
Used only if a caller doesn't supply a more specific `unavailable_reason`.
Never hardcodes "plant population UNKNOWN" here -- required_l_per_day can
be None for several different reasons (population unknown, baseline
itself unavailable for this day's stage, efficiency undetermined), and
this module has no way to know which one actually applies. Blaming
population unconditionally was a real bug: it produced a misleading
message on a real run where population WAS provided but the baseline
was unavailable for an unrelated reason (kc_development_stage). The
caller (water_model.py) knows the true cause and must pass it in.
"""


def check_available_water(
    available_water_l_per_day: float | None, required_l_per_day: float | None,
    unavailable_reason: str | None = None,
) -> FeasibilityCheck:
    if available_water_l_per_day is None:
        return FeasibilityCheck(
            "available_water", STATUS_NOT_EVALUATED,
            "available_water_l_per_day not configured for this farm -- feasibility not evaluated.",
        )
    if required_l_per_day is None:
        return FeasibilityCheck(
            "available_water", STATUS_NOT_EVALUATED,
            unavailable_reason or _DEFAULT_VOLUME_UNAVAILABLE_REASON,
        )
    ok = required_l_per_day <= available_water_l_per_day
    return FeasibilityCheck(
        "available_water", STATUS_PASS if ok else STATUS_FAIL,
        f"required {required_l_per_day:.1f} L/day vs available {available_water_l_per_day:.1f} L/day",
    )


def check_pump_capacity(
    pump_capacity_l_per_hour: float | None, required_l_per_day: float | None,
    unavailable_reason: str | None = None,
) -> FeasibilityCheck:
    if pump_capacity_l_per_hour is None:
        return FeasibilityCheck(
            "pump_capacity", STATUS_NOT_EVALUATED,
            "pump_capacity_l_per_hour not configured for this farm -- feasibility not evaluated.",
        )
    if required_l_per_day is None:
        return FeasibilityCheck(
            "pump_capacity", STATUS_NOT_EVALUATED,
            unavailable_reason or _DEFAULT_VOLUME_UNAVAILABLE_REASON,
        )
    theoretical_max_l_per_day = pump_capacity_l_per_hour * HOURS_PER_DAY
    ok = required_l_per_day <= theoretical_max_l_per_day
    return FeasibilityCheck(
        "pump_capacity", STATUS_PASS if ok else STATUS_FAIL,
        f"required {required_l_per_day:.1f} L/day vs pump's theoretical {HOURS_PER_DAY}h/day maximum "
        f"of {theoretical_max_l_per_day:.1f} L/day (continuous-operation upper bound, not a duty-cycle estimate)",
    )
