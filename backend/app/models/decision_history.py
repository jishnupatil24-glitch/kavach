from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DecisionHistory(Base):
    """
    One row per (simulation_run_id, day): the Phase 5 decision-engine
    output computed AS OF that day, for the WHOLE simulation, written
    once by the Workflow A backend processing step
    (app.services.decision_engine.history.persist_run_decisions) after
    that run's Phase 4 problem_assessment_history already exists.

    Read-only from the Phase 5 CLI/API presentation layer (Workflow B)
    -- decisions are never computed inside a presentation layer.

    `decisions_json` is a direct `dataclasses.asdict` serialization of
    app.services.decision_engine.service.decide_run's own DecisionRecord
    list (all 10 categories, always -- same auditability convention
    Phase 4 already uses), never a second, independently maintained
    representation.

    Separate table from problem_assessment_history by design: Phase 5's
    record is a new artifact (eligibility, priority, validation outcome)
    layered on top of Phase 4's evidence, not a field extension of it --
    keeps the "Phase 4 evidence logic must not change" boundary clean.
    """

    __tablename__ = "decision_history"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "day", name="uq_decision_history_run_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, index=True
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crop: Mapped[str] = mapped_column(String, nullable=False)

    decisions_json: Mapped[str] = mapped_column(Text, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
