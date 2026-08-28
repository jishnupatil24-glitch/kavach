"""
The 10 problem/stress categories Phase 4 evaluates, and what would
count as "adverse" for each -- a DEFINITIONAL mapping (which direction
of change is a concern for which variable), not an agronomic threshold.
No numeric cutoff lives here; the actual gate (trend determinacy,
persistence, ICAR-deviation sign) is in evidence.py, reusing Phase 3's
own already-computed, already-approved statistics.

Audited against the actual agronomic_parameters/stress_conditions
content (see the Phase 4 proposal) before being written -- every
category listed here is one KAVACH's Phase 3 output can actually speak
to; none were invented to look comprehensive. In particular:
  - No "excess nutrient" or "excess light" category exists -- no
    agronomic basis for either direction is present anywhere in the
    knowledge base, not even as an unpopulated placeholder.
  - `stress_conditions` (Phase 1) is NOT used as a source of numeric
    thresholds -- every row in it has threshold_value=NULL,
    status="missing" (verified by direct query during the Phase 4
    design audit). It contributes nothing usable.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProblemCategory:
    key: str
    label: str
    field: str  # matches app.services.state_analysis.current_state.CurrentState.field
    adverse_trend: str  # "RISING" | "FALLING" -- the direction of change this category is about
    adverse_icar_sign: int  # +1 = adverse when current > ICAR reference, -1 = adverse when current < ICAR reference


CATEGORIES: list[ProblemCategory] = [
    ProblemCategory("water_depletion", "Water Depletion", "soil_moisture_pct", "FALLING", -1),
    ProblemCategory("excessive_moisture", "Excessive Moisture", "soil_moisture_pct", "RISING", +1),
    ProblemCategory("heat_related", "Heat-Related", "temperature_c", "RISING", +1),
    ProblemCategory("temperature_deficit", "Temperature Deficit", "temperature_c", "FALLING", -1),
    ProblemCategory("humidity_low", "Low Humidity", "humidity_pct", "FALLING", -1),
    ProblemCategory("humidity_high", "High Humidity", "humidity_pct", "RISING", +1),
    ProblemCategory("nitrogen_related", "Nitrogen-Related", "soil_n_mg_kg", "FALLING", -1),
    ProblemCategory("phosphorus_related", "Phosphorus-Related", "soil_p_mg_kg", "FALLING", -1),
    ProblemCategory("potassium_related", "Potassium-Related", "soil_k_mg_kg", "FALLING", -1),
    ProblemCategory("light_deficit", "Light Deficit", "daily_dli_mol_m2_day", "FALLING", -1),
]
