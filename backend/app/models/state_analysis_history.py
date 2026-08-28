from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class StateAnalysisHistory(Base):
    """
    One row per (simulation_run_id, day): the Phase 3 state analysis
    computed AS OF that day, for the WHOLE simulation, written once by
    the Workflow A backend processing step
    (app.services.state_analysis.history.persist_run_history) after a
    Phase 2 run's sensor_observations already exist.

    Read-only from the Phase 3 CLI/API presentation layer (Workflow B)
    -- analysis is never computed inside a presentation layer.

    Per-parameter/stage/context detail is stored as JSON, not one
    column per field: it is a direct serialization of
    app.services.state_analysis.service.analyze_run's own dataclasses
    (via dataclasses.asdict), never a second, independently maintained
    representation of the same numbers.
    """

    __tablename__ = "state_analysis_history"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "day", name="uq_state_analysis_history_run_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, index=True
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crop: Mapped[str] = mapped_column(String, nullable=False)

    parameters_json: Mapped[str] = mapped_column(Text, nullable=False)
    crop_stages_json: Mapped[str] = mapped_column(Text, nullable=False)
    agronomic_context_json: Mapped[str] = mapped_column(Text, nullable=False)
    data_quality_notes_json: Mapped[str] = mapped_column(Text, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
