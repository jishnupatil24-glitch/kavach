from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class CropStage(Base):
    """
    Structured crop-stage reference. start_day/end_day are left NULL
    when sub-stage boundaries are not yet supported by a verified
    source -- they are never invented to fill a gap.
    """

    __tablename__ = "crop_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agronomic_sources.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
