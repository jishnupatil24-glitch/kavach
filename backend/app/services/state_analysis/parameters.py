"""
Registry of the sensor variables Phase 3 analyzes. Shared by every
state_analysis submodule so the same 7 fields/units are never defined
in more than one place.

`baseline_field` names the matching attribute on
`app.services.simulator.baseline.BaselineDay` (Phase 0's ICAR loader)
-- reused as-is, never duplicated.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParameterSpec:
    field: str  # SensorObservation attribute name
    label: str  # display label
    baseline_field: str  # matching BaselineDay attribute name (Phase 0)
    current_suffix: str  # appended to a formatted current value, e.g. " °C"
    rate_unit: str  # unit label for a per-day rate of change


PARAMETERS: list[ParameterSpec] = [
    ParameterSpec("temperature_c", "Temperature", "temperature_c", " °C", "°C/day"),
    ParameterSpec("humidity_pct", "Humidity", "humidity_pct", " %", "%/day"),
    ParameterSpec("soil_moisture_pct", "Soil Moisture", "soil_moisture_pct", " %", "pp/day"),
    ParameterSpec("daily_dli_mol_m2_day", "DLI", "dli_mol_m2_day", "", "mol/m²/day/day"),
    ParameterSpec("soil_n_mg_kg", "Soil N", "soil_n_mg_kg", "", "mg/kg/day"),
    ParameterSpec("soil_p_mg_kg", "Soil P", "soil_p_mg_kg", "", "mg/kg/day"),
    ParameterSpec("soil_k_mg_kg", "Soil K", "soil_k_mg_kg", "", "mg/kg/day"),
]
