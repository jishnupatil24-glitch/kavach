from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class StressCondition(Base):
    """
    Knowledge representation of a stress condition threshold (e.g. "water
    stress: soil_moisture_pct < X"). This is ONLY a data record -- it is
    not consumed by any diagnosis/detection logic in this phase.

    threshold_value is NULL whenever status is "missing" or
    "source_needed": an unverified number is never stored just because a
    later phase will want one.
    """

    __tablename__ = "stress_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop: Mapped[str] = mapped_column(String, nullable=False, index=True)
    stress_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    affected_parameter: Mapped[str] = mapped_column(String, nullable=False)
    operator: Mapped[str] = mapped_column(String, nullable=False)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_stages.id"), nullable=True
    )
    severity: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agronomic_sources.id"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
