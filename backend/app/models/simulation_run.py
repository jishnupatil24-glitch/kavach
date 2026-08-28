from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SimulationRun(Base):
    """
    Metadata for one virtual-sensor simulation run. A run is immutable
    once generated -- "regenerate" means creating a new run, never
    mutating an existing one, so reproducibility (same config -> same
    observations) can never be silently broken later.
    """

    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop: Mapped[str] = mapped_column(String, nullable=False, default="tomato")
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    scenario_start_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scenario_duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
