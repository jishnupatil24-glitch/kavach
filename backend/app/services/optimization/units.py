"""
Deterministic, explicit unit conversion. An unknown unit is a hard
error -- never silently interpreted or defaulted.
"""
from __future__ import annotations

ACRE_TO_M2 = 4046.8564224
HECTARE_TO_M2 = 10000.0

SUPPORTED_AREA_UNITS = ("acre", "hectare", "m2")


class UnsupportedAreaUnitError(ValueError):
    pass


def area_to_m2(value: float, unit: str) -> float:
    normalized = unit.strip().lower()
    if normalized == "acre":
        return value * ACRE_TO_M2
    if normalized == "hectare":
        return value * HECTARE_TO_M2
    if normalized == "m2":
        return value
    raise UnsupportedAreaUnitError(
        f"Unsupported field_area_unit {unit!r} -- supported units: {', '.join(SUPPORTED_AREA_UNITS)}."
    )
