import csv

from tests.conftest import EXPECTED_COLUMNS, SEED_CSV, SOURCE_PDF


def test_pdf_source_exists():
    assert SOURCE_PDF.exists(), f"Source PDF missing at {SOURCE_PDF}"
    assert SOURCE_PDF.suffix == ".pdf"


def test_seed_csv_exists():
    assert SEED_CSV.exists(), f"Seed CSV missing at {SEED_CSV}"


def test_csv_row_count():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 120


def test_csv_day_range_no_gaps_no_duplicates():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    days = [int(r["day"]) for r in rows]
    assert len(days) == len(set(days)), "duplicate day values found in CSV"
    assert sorted(days) == list(range(1, 121))


def test_csv_column_names_match_verified_pdf_structure():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == EXPECTED_COLUMNS


def test_csv_numeric_values_parse():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        int(row["day"])
        for col in EXPECTED_COLUMNS[1:]:
            float(row[col])


def test_extraction_reproduces_identical_csv(tmp_path):
    """Re-running extraction against the source PDF must reproduce the
    committed seed CSV exactly (deterministic, no drift)."""
    from app.services.extract_reference import run

    out_path = tmp_path / "tomato_reference_reextracted.csv"
    run(pdf_path=SOURCE_PDF, output_path=out_path)

    with SEED_CSV.open(encoding="utf-8") as f:
        committed = f.read()
    with out_path.open(encoding="utf-8") as f:
        reextracted = f.read()
    assert committed == reextracted
