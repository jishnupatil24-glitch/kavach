"""
Extracts the ICAR tomato polyhouse reference table from the source PDF
into a structured, verified CSV.

This script performs NO estimation, interpolation, or correction of values.
It only parses what is literally present in the PDF table and validates
structural expectations (day range, row count, numeric parseability).

Run manually / via seed process:
    python -m app.services.extract_reference
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pdfplumber

REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_PDF = REPO_ROOT / "data" / "sources" / "icar" / "tomato_reference.pdf"
OUTPUT_CSV = REPO_ROOT / "data" / "seed" / "tomato_reference.csv"

# Clean machine-readable column names, in the exact order columns appear
# in the source PDF table. The PDF's header text has corrupted glyphs for
# degree/superscript/subscript characters (font encoding issue in the
# source document) -- these names are resolved from known agronomic
# notation (P2O5, K2O), not guessed values. No numeric data is altered.
COLUMNS = [
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

EXPECTED_NUM_COLUMNS = 11
EXPECTED_DAY_MIN = 1
EXPECTED_DAY_MAX = 120
EXPECTED_ROW_COUNT = 120


class ExtractionError(Exception):
    pass


def _is_header_row(row: list[str]) -> bool:
    return row[0].strip().lower() == "day"


def extract_rows(pdf_path: Path) -> list[list[str]]:
    if not pdf_path.exists():
        raise ExtractionError(f"Source PDF not found: {pdf_path}")

    all_rows: list[list[str]] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()
            if len(tables) != 1:
                raise ExtractionError(
                    f"Page {page_num}: expected exactly 1 table, found {len(tables)}"
                )
            table = tables[0]
            for row in table:
                if row is None:
                    raise ExtractionError(f"Page {page_num}: encountered a null row")
                if len(row) != EXPECTED_NUM_COLUMNS:
                    raise ExtractionError(
                        f"Page {page_num}: row has {len(row)} columns, "
                        f"expected {EXPECTED_NUM_COLUMNS}: {row}"
                    )
                if _is_header_row(row):
                    continue  # header repeats on every page
                all_rows.append(row)
    return all_rows


def validate_and_parse(raw_rows: list[list[str]]) -> list[dict]:
    if len(raw_rows) != EXPECTED_ROW_COUNT:
        raise ExtractionError(
            f"Expected {EXPECTED_ROW_COUNT} data rows, found {len(raw_rows)}"
        )

    parsed: list[dict] = []
    seen_days: set[int] = set()
    problems: list[str] = []

    for row in raw_rows:
        record: dict = {}
        for col_name, raw_value in zip(COLUMNS, row):
            if raw_value is None or str(raw_value).strip() == "":
                problems.append(f"missing value for '{col_name}' in row {row}")
                record[col_name] = None
                continue
            value_str = str(raw_value).strip()
            try:
                if col_name == "day":
                    record[col_name] = int(value_str)
                else:
                    record[col_name] = float(value_str)
            except ValueError:
                problems.append(
                    f"malformed value '{value_str}' for '{col_name}' in row {row}"
                )
                record[col_name] = None

        parsed.append(record)

    if problems:
        raise ExtractionError(
            "Extraction validation failed with the following problems:\n"
            + "\n".join(f"  - {p}" for p in problems)
        )

    for record in parsed:
        day = record["day"]
        if day in seen_days:
            raise ExtractionError(f"Duplicate day value found: {day}")
        seen_days.add(day)

    expected_days = set(range(EXPECTED_DAY_MIN, EXPECTED_DAY_MAX + 1))
    missing_days = expected_days - seen_days
    unexpected_days = seen_days - expected_days
    if missing_days:
        raise ExtractionError(f"Missing day values: {sorted(missing_days)}")
    if unexpected_days:
        raise ExtractionError(f"Unexpected day values: {sorted(unexpected_days)}")

    parsed.sort(key=lambda r: r["day"])
    return parsed


def write_csv(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def run(pdf_path: Path = SOURCE_PDF, output_path: Path = OUTPUT_CSV) -> list[dict]:
    raw_rows = extract_rows(pdf_path)
    records = validate_and_parse(raw_rows)
    write_csv(records, output_path)
    return records


if __name__ == "__main__":
    try:
        result = run()
    except ExtractionError as e:
        print(f"EXTRACTION FAILED:\n{e}", file=sys.stderr)
        sys.exit(1)
    print(f"Extracted and validated {len(result)} rows -> {OUTPUT_CSV}")
