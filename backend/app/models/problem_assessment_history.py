from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ProblemAssessmentHistory(Base):
    """
    One row per (simulation_run_id, day): the Phase 4 evidence-based
    problem/stress assessment computed AS OF that day, for the WHOLE
    simulation, written once by the Workflow A backend processing step
    (app.services.stress_assessment.history.persist_run_assessments)
    after that run's Phase 3 state_analysis_history already exists.

    Read-only from the Phase 4 CLI/API presentation layer (Workflow B)
    -- assessment is never computed inside a presentation layer.

    `problems_json` is a direct `dataclasses.asdict` serialization of
    app.services.stress_assessment.service.assess_run's own
    ProblemAssessment list (all 10 categories, always -- see that
    module's docstring), never a second, independently maintained
    representation of the same evidence.
    """

    __tablename__ = "problem_assessment_history"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "day", name="uq_problem_assessment_history_run_day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, index=True
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    crop: Mapped[str] = mapped_column(String, nullable=False)

    problems_json: Mapped[str] = mapped_column(Text, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
