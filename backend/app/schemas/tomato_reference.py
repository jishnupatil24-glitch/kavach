from pydantic import BaseModel, ConfigDict


class TomatoReferenceProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: int
    soil_moisture_pct: float
    temperature_c: float
    humidity_pct: float
    dli_mol_m2_day: float
    soil_n_mg_kg: float
    soil_p_mg_kg: float
    soil_k_mg_kg: float
    n_demand_g_plant_day: float
    p2o5_demand_g_plant_day: float
    k2o_demand_g_plant_day: float
