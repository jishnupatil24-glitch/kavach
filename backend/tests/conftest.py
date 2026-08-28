from pathlib import Path

import pytest

# Importing app.main pulls in every route module, which transitively
# imports every SQLAlchemy model. This must happen before any fixture
# calls Base.metadata.create_all() -- otherwise tables for models that
# happen not to be imported yet (e.g. simulator models, if no earlier
# import touched them) would silently never get created, regardless of
# fixture execution order.
from app import main as _main  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PDF = REPO_ROOT / "data" / "sources" / "icar" / "tomato_reference.pdf"
SEED_CSV = REPO_ROOT / "data" / "seed" / "tomato_reference.csv"

EXPECTED_COLUMNS = [
    "day",
    "soil_moisture_pct",
    "temperature_c",
    "humidity_pct",
    "dli_mol_m2_day",
    "soil_n_mg_kg",
    "soil_p_mg_kg",
    "soil_k_mg_kg",
    "n_demand_g_plant_day",
    "p2o5_demand_g_plant_day",
    "k2o_demand_g_plant_day",
]


@pytest.fixture(scope="session")
def seeded_db():
    """
    Seeds the real SQLite database from the seed CSV once per test session,
    then yields a session factory for tests to query against.
    """
    from app.database.session import SessionLocal
    from app.services.seed_database import seed

    seed()
    yield SessionLocal


@pytest.fixture(scope="session")
def seeded_agronomics_db(seeded_db):
    """
    Seeds the agronomic knowledge base (sources, stages, parameters,
    stress conditions). Depends on seeded_db so both seed steps run
    against the same initialized database before any test queries it.
    """
    from app.services.seed_agronomics import seed as seed_agronomics

    counts = seed_agronomics()
    return counts


@pytest.fixture(scope="session")
def api_client(seeded_db, seeded_agronomics_db):
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)
