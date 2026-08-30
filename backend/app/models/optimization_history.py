from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class OptimizationHistory(Base):
    """
    One row per (simulation_run_id, day): the Phase 6 quantitative
    optimization output computed AS OF that day, written once by the
    Workflow A backend processing step
    (app.services.optimization.history.persist_run_optimizations)
    after that run's Phase 5 decision_history already exists.

    Read-only from the Phase 6 CLI/API presentation layer (Workflow B)
    -- optimizations are never computed inside a presentation layer.

    `optimization_json` is a direct `dataclasses.asdict` serialization
    of app.services.optimization.service.optimize_run's own
    OptimizationAssessment, never a second, independently maintained
    representation -- same auditability convention every earlier
    phase's history table already uses.

    Separate table from decision_history by design: Phase 6's record
    is a new artifact (quantities, farm configuration used, provenance)
    layered on top of Phase 5's decision, not a field extension of it.
    """

    __tablename__ = "optimization_history"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "day", name="uq_optimization_history_run_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, index=True
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crop: Mapped[str] = mapped_column(String, nullable=False)

    optimization_json: Mapped[str] = mapped_column(Text, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
