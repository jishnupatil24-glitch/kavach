"""
Reads the frozen ICAR reference trajectory (Phase 0) as the simulator's
baseline. Read-only -- never writes to tomato_reference_profile.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.tomato_reference import TomatoReferenceProfile


@dataclass(frozen=True)
class BaselineDay:
    day: int
    temperature_c: float
    humidity_pct: float
    soil_moisture_pct: float
    dli_mol_m2_day: float
    soil_n_mg_kg: float
    soil_p_mg_kg: float
    soil_k_mg_kg: float


def load_baseline(db: Session) -> dict[int, BaselineDay]:
    """Loads all 120 ICAR reference days, keyed by day number."""
    rows = db.query(TomatoReferenceProfile).order_by(TomatoReferenceProfile.day).all()
    return {
        r.day: BaselineDay(
            day=r.day,
            temperature_c=r.temperature_c,
            humidity_pct=r.humidity_pct,
            soil_moisture_pct=r.soil_moisture_pct,
            dli_mol_m2_day=r.dli_mol_m2_day,
            soil_n_mg_kg=r.soil_n_mg_kg,
            soil_p_mg_kg=r.soil_p_mg_kg,
            soil_k_mg_kg=r.soil_k_mg_kg,
        )
        for r in rows
    }
