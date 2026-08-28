from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class AgronomicParameter(Base):
    """
    A single sourced-or-not agricultural parameter for a crop (e.g. Kc,
    a temperature bound, a soil characteristic). Distinct from
    `tomato_reference_profile`, which holds the day-by-day ICAR
    trajectory -- this table holds general/stage-specific knowledge used
    to interpret that trajectory, not another copy of it.

    `status` must be one of AGRONOMIC_STATUS_VALUES:
      - "sourced": has a real value (value_numeric OR value_min/value_max)
        and a non-null source_id.
      - "assumption": a modelling assumption, not presented as fact.
      - "missing" / "source_needed": no verifiable value or source exists
        yet -- value_numeric/value_min/value_max/value_text/source_id are
        all NULL. Never fabricated to fill a gap.
      - "derived": the parameter is a computed quantity (e.g. ETo, ETc),
        never a fixed lookup fact -- value fields stay NULL forever, even
        once inputs exist; the computation happens in a future service,
        not here. `notes` documents the formula/inputs.
      - "context_dependent": the parameter is real but site/config
        specific (e.g. soil field capacity depends on soil texture) --
        value fields stay NULL; `source_id` may still point at a
        *definitional* source even though no single number applies.

    A value is stored as exactly one of:
      - a single point: value_numeric set, value_min/value_max NULL.
      - a range: value_min/value_max set, value_numeric NULL.
      - neither (missing/source_needed/derived/context_dependent).
    The CHECK constraint below enforces value_numeric and value_min are
    never both populated on the same row -- a sourced value is never
    allowed to look like an arbitrary midpoint of a range, and vice versa.
    """

    __tablename__ = "agronomic_parameters"
    __table_args__ = (
        CheckConstraint(
            "NOT (value_numeric IS NOT NULL AND value_min IS NOT NULL)",
            name="ck_agronomic_parameter_value_exclusive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop: Mapped[str] = mapped_column(String, nullable=False, index=True)
    domain: Mapped[str] = mapped_column(String, nullable=False, index=True)
    parameter_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    value_numeric: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    stage_id: Mapped[int | None] = mapped_column(
        ForeignKey("crop_stages.id"), nullable=True
    )
    context: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[int | None] = mapped_column(
        ForeignKey("agronomic_sources.id"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
