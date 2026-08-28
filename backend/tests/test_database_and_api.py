import csv

from tests.conftest import EXPECTED_COLUMNS, SEED_CSV


def _load_csv_rows():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_db_record_count_matches_csv(seeded_db):
    from app.models.tomato_reference import TomatoReferenceProfile

    db = seeded_db()
    try:
        count = db.query(TomatoReferenceProfile).count()
    finally:
        db.close()
    assert count == len(_load_csv_rows()) == 120


def test_db_day_values_exactly_1_to_120(seeded_db):
    from app.models.tomato_reference import TomatoReferenceProfile

    db = seeded_db()
    try:
        days = sorted(r.day for r in db.query(TomatoReferenceProfile).all())
    finally:
        db.close()
    assert days == list(range(1, 121))


def test_db_values_match_csv(seeded_db):
    from app.models.tomato_reference import TomatoReferenceProfile

    csv_rows = {int(r["day"]): r for r in _load_csv_rows()}

    db = seeded_db()
    try:
        db_rows = db.query(TomatoReferenceProfile).all()
    finally:
        db.close()

    assert len(db_rows) == len(csv_rows)
    for record in db_rows:
        csv_row = csv_rows[record.day]
        for col in EXPECTED_COLUMNS[1:]:
            assert getattr(record, col) == float(csv_row[col]), (
                f"mismatch on day {record.day}, field {col}"
            )


def test_api_get_day_1(api_client):
    resp = api_client.get("/api/reference/tomato/day/1")
    assert resp.status_code == 200
    body = resp.json()
    assert body["day"] == 1
    assert body["soil_moisture_pct"] == 75.0


def test_api_get_day_47(api_client):
    resp = api_client.get("/api/reference/tomato/day/47")
    assert resp.status_code == 200
    body = resp.json()
    assert body["day"] == 47
    csv_row = {int(r["day"]): r for r in _load_csv_rows()}[47]
    for col in EXPECTED_COLUMNS[1:]:
        assert body[col] == float(csv_row[col])


def test_day_47_identical_across_csv_db_orm_api(seeded_db, api_client):
    """
    Regression test: pins the exact Day 47 record and cross-checks it
    across every layer (CSV -> SQLite raw row -> SQLAlchemy ORM object ->
    Pydantic schema -> live FastAPI JSON) so any future field-name typo
    or serialization drift (e.g. a bad `alias`/`Field` mapping) fails
    loudly instead of silently reaching the API response.
    """
    import sqlite3

    from app.database.session import DB_PATH
    from app.models.tomato_reference import TomatoReferenceProfile
    from app.schemas.tomato_reference import TomatoReferenceProfileOut

    expected = {
        "day": 47,
        "soil_moisture_pct": 75.0,
        "temperature_c": 26.0,
        "humidity_pct": 60.0,
        "dli_mol_m2_day": 20.0,
        "soil_n_mg_kg": 177.0,
        "soil_p_mg_kg": 33.0,
        "soil_k_mg_kg": 319.0,
        "n_demand_g_plant_day": 0.135,
        "p2o5_demand_g_plant_day": 0.03,
        "k2o_demand_g_plant_day": 0.155,
    }

    # CSV
    csv_row = {int(r["day"]): r for r in _load_csv_rows()}[47]
    csv_values = {"day": 47} | {c: float(csv_row[c]) for c in EXPECTED_COLUMNS[1:]}
    assert csv_values == expected

    # Raw SQLite
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "SELECT * FROM tomato_reference_profile WHERE day=47"
    ).fetchone()
    con.close()
    sqlite_values = {c: row[c] for c in expected}
    assert sqlite_values == expected

    # SQLAlchemy ORM object
    db = seeded_db()
    try:
        obj = db.query(TomatoReferenceProfile).filter_by(day=47).first()
        orm_values = {c: getattr(obj, c) for c in expected}
        assert orm_values == expected

        # Pydantic schema
        schema_values = TomatoReferenceProfileOut.model_validate(obj).model_dump()
        assert schema_values == expected
    finally:
        db.close()

    # Live FastAPI JSON
    resp = api_client.get("/api/reference/tomato/day/47")
    assert resp.status_code == 200
    assert resp.json() == expected
    assert "soil_moic" not in resp.text
    assert "31935" not in resp.text


def test_api_get_day_120(api_client):
    resp = api_client.get("/api/reference/tomato/day/120")
    assert resp.status_code == 200
    assert resp.json()["day"] == 120


def test_api_get_day_121_not_found(api_client):
    resp = api_client.get("/api/reference/tomato/day/121")
    assert resp.status_code == 404


def test_api_list_reference_returns_120(api_client):
    resp = api_client.get("/api/reference/tomato")
    assert resp.status_code == 200
    assert len(resp.json()) == 120
