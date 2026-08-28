from sqlalchemy import Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class SensorObservation(Base):
    """
    One virtual-sensor reading, at 6-hour resolution. This table is
    designed to look exactly like what a REAL sensor deployment would
    eventually produce -- a future real-sensor integration should be
    able to write into this same shape, so KAVACH's future decision
    logic never needs to know whether a row came from the simulator or
    a physical sensor.

    `daily_dli_mol_m2_day` is a DAILY-INTEGRAL quantity (mol/m2/day),
    duplicated across all four 6-hour observations of the same day for
    query convenience. It is NEVER a 6-hour instantaneous reading --
    treat 4 rows on the same day as 1 light measurement, not 4.

    Demand fields (n_demand_g_plant_day, p2o5_demand_g_plant_day,
    k2o_demand_g_plant_day) are intentionally NOT simulated here -- no
    physical sensor measures "demand", only concentration.
    """

    __tablename__ = "sensor_observations"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "day", "hour", name="uq_sensor_observation_run_day_hour"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[int] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=False, index=True
    )
    day: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    hour: Mapped[int] = mapped_column(Integer, nullable=False)  # one of 0, 6, 12, 18

    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    soil_moisture_pct: Mapped[float] = mapped_column(Float, nullable=False)
    daily_dli_mol_m2_day: Mapped[float] = mapped_column(Float, nullable=False)
    soil_n_mg_kg: Mapped[float] = mapped_column(Float, nullable=False)
    soil_p_mg_kg: Mapped[float] = mapped_column(Float, nullable=False)
    soil_k_mg_kg: Mapped[float] = mapped_column(Float, nullable=False)
