"""
Imports the verified reference CSV into SQLite.

    data/seed/tomato_reference.csv -> tomato_reference_profile table

Reproducible: drops and recreates the reference table content from the
CSV each run, so the database is always derivable from the CSV artifact.
Does not read the source PDF directly.

Run:
    python -m app.services.seed_database
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from app.database.session import Base, SessionLocal, engine
from app.models.data_source import DataSource
from app.models.tomato_reference import TomatoReferenceProfile

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "data" / "seed" / "tomato_reference.csv"
SOURCE_PDF_RELATIVE = "data/sources/icar/tomato_reference.pdf"

NUMERIC_FIELDS = [
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


def load_csv_records(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Seed CSV not found: {csv_path}")

    records = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            record = {"day": int(row["day"])}
            for field in NUMERIC_FIELDS:
                record[field] = float(row[field])
            records.append(record)
    return records


def seed(csv_path: Path = CSV_PATH) -> int:
    records = load_csv_records(csv_path)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(TomatoReferenceProfile).delete()
        for record in records:
            db.add(TomatoReferenceProfile(**record))

        if not db.query(DataSource).filter_by(file_path=SOURCE_PDF_RELATIVE).first():
            db.add(
                DataSource(
                    name="ICAR-derived tomato reference dataset",
                    source_type="PDF",
                    file_path=SOURCE_PDF_RELATIVE,
                    notes=(
                        "Author, publication date, and institution details "
                        "are not present in the source document and are "
                        "left unknown rather than invented."
                    ),
                )
            )

        db.commit()
    finally:
        db.close()

    return len(records)


if __name__ == "__main__":
    try:
        count = seed()
    except FileNotFoundError as e:
        print(f"SEED FAILED: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Seeded {count} reference rows into database.")
