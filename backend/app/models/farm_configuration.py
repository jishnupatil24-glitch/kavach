from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FarmConfiguration(Base):
    """
    Farm-specific configuration for ONE simulation run -- Phase 6 input,
    deliberately separate from `agronomic_parameters` (which holds
    general/stage-specific agricultural KNOWLEDGE, not farm-specific
    facts like "this simulated farm has 8,000 plants"). One row per
    `simulation_run_id` (upsertable, unlike the append-only/immutable
    convention every other Phase 2-5 table uses) -- farm configuration
    is corrective input a farmer can update, not a measurement or a
    computed result.

    Only `field_area`/`field_area_unit`/`crop` are required (NOT NULL).
    Everything else is optional -- Phase 6 must work without any of it,
    reporting UNKNOWN/UNAVAILABLE/NOT_EVALUATED rather than inventing a
    value, per the approved Phase 6 design.
    """

    __tablename__ = "farm_configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, unique=True, index=True
    )
    crop: Mapped[str] = mapped_column(String, nullable=False)
    field_area: Mapped[float] = mapped_column(Float, nullable=False)
    field_area_unit: Mapped[str] = mapped_column(String, nullable=False)

    plant_population: Mapped[int | None] = mapped_column(Integer, nullable=True)
    plant_spacing_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    row_spacing_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    cultivar: Mapped[str | None] = mapped_column(String, nullable=True)

    irrigation_system_type: Mapped[str | None] = mapped_column(String, nullable=True)
    irrigation_efficiency_pct: Mapped[float | None] = mapped_column(Float, nullable=True)

    available_water_l_per_day: Mapped[float | None] = mapped_column(Float, nullable=True)
    pump_capacity_l_per_hour: Mapped[float | None] = mapped_column(Float, nullable=True)
    pump_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)

    water_cost_per_liter: Mapped[float | None] = mapped_column(Float, nullable=True)
    fertilizer_cost_per_kg_n: Mapped[float | None] = mapped_column(Float, nullable=True)
    fertilizer_cost_per_kg_p2o5: Mapped[float | None] = mapped_column(Float, nullable=True)
    fertilizer_cost_per_kg_k2o: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )
