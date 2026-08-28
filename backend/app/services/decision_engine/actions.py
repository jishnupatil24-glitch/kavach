"""
Phase 5 action-label vocabulary -- a DEFINITIONAL mapping (which
qualitative, directional action corresponds to which Phase 4 category),
not agronomic knowledge. Mirrors app.services.stress_assessment
.categories's own "definitional mapping, not a sourced fact" precedent.

Every label is qualitative/directional ONLY -- never a quantity, a
unit, a dose, or a rate. No numeric intervention parameter exists
anywhere in this project's knowledge base (confirmed by repository
audit), so no action label here may imply one. See
app.services.decision_engine.validation for how the decision record
makes this explicit (action_type="QUALITATIVE", quantitative_basis
always None, with a stated limitation).

Approved verbatim wording -- do not reword without re-approval.
"""
from __future__ import annotations

ACTION_LABELS: dict[str, str] = {
    "water_depletion": "Increase irrigation",
    "excessive_moisture": "Reduce irrigation",
    "heat_related": "Address heat stress",
    "temperature_deficit": "Address cold stress",
    "humidity_low": "Increase humidity",
    "humidity_high": "Reduce humidity",
    "nitrogen_related": "Review nitrogen program",
    "phosphorus_related": "Review phosphorus program",
    "potassium_related": "Review potassium program",
    "light_deficit": "Review supplemental lighting",
}


def get_action_label(category_key: str) -> str | None:
    return ACTION_LABELS.get(category_key)
