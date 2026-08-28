from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AgronomicSource(Base):
    """
    Provenance record for agronomic knowledge (distinct from Phase 0's
    `data_source`, which records provenance for the day-by-day ICAR
    reference profile). Any field we cannot verify from the actual
    document is left NULL rather than invented.
    """

    __tablename__ = "agronomic_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_or_author: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)
    document_reference: Mapped[str | None] = mapped_column(String, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
