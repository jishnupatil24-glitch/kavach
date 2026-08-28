from sqlalchemy import Float, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class TomatoReferenceProfile(Base):
    """
    ICAR-derived reference tomato polyhouse profile.

    This is a REFERENCE dataset (expected/baseline crop trajectory for
    Day 1-120), not live sensor data and not a "ground truth" claim beyond
    what the source document itself states.
    """

    __tablename__ = "tomato_reference_profile"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    day: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)

    soil_moisture_pct: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_c: Mapped[float] = mapped_column(Float, nullable=False)
    humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    dli_mol_m2_day: Mapped[float] = mapped_column(Float, nullable=False)
    soil_n_mg_kg: Mapped[float] = mapped_column(Float, nullable=False)
    soil_p_mg_kg: Mapped[float] = mapped_column(Float, nullable=False)
    soil_k_mg_kg: Mapped[float] = mapped_column(Float, nullable=False)
    n_demand_g_plant_day: Mapped[float] = mapped_column(Float, nullable=False)
    p2o5_demand_g_plant_day: Mapped[float] = mapped_column(Float, nullable=False)
    k2o_demand_g_plant_day: Mapped[float] = mapped_column(Float, nullable=False)
