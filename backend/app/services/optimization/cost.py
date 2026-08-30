"""
Cost calculation only when the required farmer-supplied cost
parameter is actually configured. Never invents a monetary value.
"""
from __future__ import annotations

from dataclasses import dataclass

STATUS_AVAILABLE = "AVAILABLE"
STATUS_UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class CostResult:
    status: str  # AVAILABLE | UNAVAILABLE
    baseline_cost: float | None
    optimized_cost: float | None
    cost_change: float | None  # optimized - baseline: positive = more expensive, negative = saving
    detail: str


def compute_cost(
    unit_cost: float | None,
    baseline_quantity: float | None,
    optimized_quantity: float | None,
    quantity_label: str,
    unavailable_reason: str | None = None,
) -> CostResult:
    if unit_cost is None:
        return CostResult(
            STATUS_UNAVAILABLE, None, None, None,
            f"No cost rate configured for {quantity_label} -- cost UNAVAILABLE.",
        )
    if baseline_quantity is None or optimized_quantity is None:
        # Do NOT hardcode a single cause here -- a None quantity can mean
        # population is unknown, or the baseline/optimized quantity itself
        # was unavailable for an unrelated reason. The caller knows which.
        return CostResult(
            STATUS_UNAVAILABLE, None, None, None,
            unavailable_reason or f"Field-level {quantity_label} quantity is unavailable -- cost UNAVAILABLE.",
        )
    baseline_cost = baseline_quantity * unit_cost
    optimized_cost = optimized_quantity * unit_cost
    return CostResult(
        STATUS_AVAILABLE, baseline_cost, optimized_cost, optimized_cost - baseline_cost,
        f"{quantity_label} cost at configured rate {unit_cost} per unit.",
    )
