from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class DataSource(Base):
    """
    Minimal provenance record for imported reference data.

    Only fields we can actually verify from the source document are
    populated. Anything not present in the source (author, publication
    date, institution, URL, etc.) is left as "unknown" rather than
    invented.
    """

    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str] = mapped_column(String, nullable=True)
