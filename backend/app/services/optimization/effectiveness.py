"""
Expected outcome: qualitative-direction-only, MODELED, never a
recovery-time or magnitude claim. No forecasting, no soil-moisture-
response physics -- see the approved Phase 6 design's explicit ban on
both.
"""
from __future__ import annotations

EXPECTED_OUTCOME_BASIS = "MODELED EXPECTED DIRECTION"


def expected_direction(adverse_trend: str) -> str:
    """
    A successful intervention is expected to move the variable AWAY
    FROM the adverse direction that triggered detection in the first
    place -- the direct inverse of Phase 4's own
    `ProblemCategory.adverse_trend`, not a second, independently
    invented direction table.
    """
    return "FALLING" if adverse_trend == "RISING" else "RISING"
