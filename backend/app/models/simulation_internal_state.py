from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SimulationInternalState(Base):
    """
    Debug/traceability-only record of the simulator's internal control
    variables for one 6-hour slot (irrigation input, evaporative loss,
    scenario deltas). This is NEVER a physical sensor reading and NEVER
    a farmer-facing recommendation -- it exists purely so the causal
    mechanism (why did soil moisture move the way it did) can be
    inspected and tested, kept separate from `sensor_observations` so
    that table stays a clean "what a real sensor would report" shape.
    """

    __tablename__ = "simulation_internal_state"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "day", "hour", name="uq_simulation_internal_state_run_day_hour"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, index=True
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)

    irrigation_input_pct: Mapped[float] = mapped_column(Float, nullable=False)
    evaporative_loss_pct: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_delta_from_scenario: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_delta_from_scenario: Mapped[float] = mapped_column(Float, nullable=False)
