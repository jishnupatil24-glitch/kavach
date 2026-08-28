import csv

from tests.conftest import EXPECTED_COLUMNS, SEED_CSV


def _load_csv_rows():
    with SEED_CSV.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_agronomic_source_created_and_retrievable(seeded_agronomics_db, api_client):
    resp = api_client.get("/api/agronomics/tomato/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) == 11
    icar = sources[0]
    assert icar["title"] == "ICAR-derived tomato polyhouse dataset"
    assert icar["source_type"] == "PDF"
    assert icar["document_reference"] == "data/sources/icar/tomato_reference.pdf"
    # Not fabricated: unverifiable fields stay null, not guessed.
    assert icar["organization_or_author"] is None
    assert icar["publication_year"] is None


def test_crop_stages_span_two_independent_taxonomies(api_client):
    """
    Two independent, source-tied stage taxonomies coexist (ICAR full-cycle
    + Sharma & Changade DAS-based Kc stages + DAF Qld phenological
    stages) -- 9 stages total, never merged into one.
    """
    resp = api_client.get("/api/agronomics/tomato/stages")
    assert resp.status_code == 200
    stages = {s["name"]: s for s in resp.json()}
    assert len(stages) == 9

    full_cycle = stages["full_cycle"]
    assert full_cycle["start_day"] == 1
    assert full_cycle["end_day"] == 120
    assert full_cycle["source_id"] is not None

    # DAS-based Kc stage: real day window, sourced.
    kc_initial_stage = stages["kc_initial_stage"]
    assert kc_initial_stage["start_day"] == 1
    assert kc_initial_stage["end_day"] == 26
    assert kc_initial_stage["source_id"] is not None

    # DAF Qld phenological stage: no day-number mapping given by the
    # source, so boundaries are left NULL rather than invented.
    germination = stages["germination"]
    assert germination["start_day"] is None
    assert germination["end_day"] is None
    assert germination["source_id"] is not None

    resp2 = api_client.get(f"/api/agronomics/tomato/stages/{full_cycle['id']}")
    assert resp2.status_code == 200
    assert resp2.json() == full_cycle


def test_stage_linked_parameters_reference_real_stage_rows(api_client):
    """
    Stage association happens via the real stage_id FK, never via a
    stage name stuffed into a text field.
    """
    stages_by_id = {s["id"]: s for s in api_client.get("/api/agronomics/tomato/stages").json()}

    kc_initial_records = api_client.get("/api/agronomics/tomato/parameters/kc_initial").json()
    polyhouse_row = next(
        r for r in kc_initial_records if "polyhouse" in (r["context"] or "")
    )
    assert polyhouse_row["stage_id"] is not None
    linked_stage = stages_by_id[polyhouse_row["stage_id"]]
    assert linked_stage["name"] == "kc_initial_stage"
    assert linked_stage["start_day"] == 1
    assert linked_stage["end_day"] == 26

    # Non-stage-specific parameters correctly have no stage link.
    soil_ph = api_client.get("/api/agronomics/tomato/parameters/soil_ph").json()
    assert all(r["stage_id"] is None for r in soil_ph)


def test_parameter_status_source_id_consistency(api_client):
    """
    - status="sourced" must always carry a non-null source_id.
    - status in (missing, source_needed) must never carry a source_id.
    - status in (derived, context_dependent) may cite a methodological/
      definitional source_id, but must never carry a stored value.
    """
    resp = api_client.get("/api/agronomics/tomato/parameters")
    assert resp.status_code == 200
    params = resp.json()
    assert len(params) == 40

    for p in params:
        if p["status"] == "sourced":
            assert p["source_id"] is not None
        elif p["status"] in ("missing", "source_needed"):
            assert p["source_id"] is None
            assert p["value_numeric"] is None
            assert p["value_min"] is None
            assert p["value_max"] is None
            assert p["value_text"] is None
        elif p["status"] in ("derived", "context_dependent"):
            assert p["value_numeric"] is None
            assert p["value_min"] is None
            assert p["value_max"] is None


def test_sourced_parameter_cannot_silently_lose_provenance(api_client):
    """
    Every parameter marked status="sourced" must carry a non-null
    source_id AND an actual value (single, range, or text) -- a sourced
    value is never allowed to look identical to a placeholder.
    """
    resp = api_client.get("/api/agronomics/tomato/parameters?status=sourced")
    assert resp.status_code == 200
    sourced = resp.json()
    assert len(sourced) > 0
    for p in sourced:
        assert p["source_id"] is not None
        has_value = (
            p["value_numeric"] is not None
            or p["value_min"] is not None
            or p["value_text"] is not None
        )
        assert has_value, f"sourced row with no value at all: {p}"


def test_value_representation_never_mixes_point_and_range(api_client):
    """
    A row is a single point OR a range, never both -- mirrors the DB
    CHECK constraint at the API level for every currently stored row.
    """
    resp = api_client.get("/api/agronomics/tomato/parameters")
    for p in resp.json():
        assert not (p["value_numeric"] is not None and p["value_min"] is not None)


def test_value_exclusivity_check_constraint_enforced_at_db_level():
    """
    The CHECK constraint itself must reject a row with both
    value_numeric and value_min populated -- not just a convention the
    seed script happens to follow.
    """
    import pytest
    from sqlalchemy.exc import IntegrityError

    from app.database.session import SessionLocal
    from app.models.agronomic_parameter import AgronomicParameter

    db = SessionLocal()
    try:
        db.add(
            AgronomicParameter(
                crop="tomato",
                domain="water",
                parameter_name="__test_invalid_row__",
                value_numeric=1.0,
                value_min=0.5,
                value_max=1.5,
                status="sourced",
            )
        )
        with pytest.raises(IntegrityError):
            db.flush()
    finally:
        db.rollback()
        db.close()


def test_ranges_are_not_collapsed_to_a_midpoint(api_client):
    soil_ph = api_client.get("/api/agronomics/tomato/parameters/soil_ph").json()
    assert len(soil_ph) == 1
    assert soil_ph[0]["value_numeric"] is None
    assert soil_ph[0]["value_min"] == 6.0
    assert soil_ph[0]["value_max"] == 6.8

    root_depth = api_client.get("/api/agronomics/tomato/parameters/root_zone_depth_cm").json()
    assert len(root_depth) == 1
    assert root_depth[0]["value_numeric"] is None
    assert root_depth[0]["value_min"] == 70.0
    assert root_depth[0]["value_max"] == 150.0


def test_conflicting_source_values_are_both_preserved_not_averaged(api_client):
    """
    DAF Qld's own Table 1 and body text disagree on germination's upper
    critical temperature (25 vs 35). Both must be stored as separate
    rows -- never averaged (30) or silently resolved to one.
    """
    records = api_client.get("/api/agronomics/tomato/parameters/temperature_max_c").json()
    stages = {s["id"]: s["name"] for s in api_client.get("/api/agronomics/tomato/stages").json()}
    germination_records = [r for r in records if stages.get(r["stage_id"]) == "germination"]
    assert len(germination_records) == 2
    values = {r["value_numeric"] for r in germination_records}
    assert values == {25.0, 35.0}


def test_units_are_stored_for_parameters_that_have_them(api_client):
    resp = api_client.get("/api/agronomics/tomato/parameters/temperature_max_c")
    assert resp.status_code == 200
    records = resp.json()
    assert len(records) == 5
    assert all(r["unit"] == "°C" for r in records)


def test_unresolved_parameters_are_explicit_not_fabricated(api_client):
    resp = api_client.get("/api/agronomics/tomato/parameters?status=source_needed")
    assert resp.status_code == 200
    unresolved = resp.json()
    assert len(unresolved) > 0
    names = {p["parameter_name"] for p in unresolved}
    assert "soil_bulk_density_g_cm3" in names
    for p in unresolved:
        assert p["value_numeric"] is None
        assert p["value_min"] is None
        assert p["value_max"] is None
        assert p["value_text"] is None
        assert p["source_id"] is None


def test_derived_parameters_never_store_a_computed_value(api_client):
    for name in (
        "eto_reference_mm_day",
        "crop_water_requirement_mm_day",
        "soil_available_water_capacity_mm",
    ):
        records = api_client.get(f"/api/agronomics/tomato/parameters/{name}").json()
        assert len(records) == 1
        record = records[0]
        assert record["status"] == "derived"
        assert record["value_numeric"] is None
        assert record["value_min"] is None
        assert record["value_max"] is None
        assert record["notes"]  # formula/inputs must be documented


def test_context_dependent_parameters_never_store_a_universal_value(api_client):
    for name in ("soil_field_capacity_pct", "soil_permanent_wilting_point_pct", "soil_texture", "irrigation_efficiency_pct"):
        records = api_client.get(f"/api/agronomics/tomato/parameters/{name}").json()
        assert len(records) == 1
        record = records[0]
        assert record["status"] == "context_dependent"
        assert record["value_numeric"] is None
        assert record["value_min"] is None
        assert record["value_max"] is None


def test_kc_values_are_now_sourced_with_full_provenance(api_client):
    """
    Phase 1.5B verified the Kc trio (0.53/1.08/0.63) against a
    peer-reviewed polyhouse-specific study -- they are no longer
    withheld. Each parameter name now has 3 rows (one per cultivation
    system studied), each with real provenance.
    """
    expected = {
        "kc_initial": {"polyhouse": 0.53, "shade": 0.51, "open field": 0.51},
        "kc_mid": {"polyhouse": 1.08, "shade": 1.05, "open field": 1.10},
        "kc_late": {"polyhouse": 0.63, "shade": 0.61, "open field": 0.67},
    }
    for name, variants in expected.items():
        records = api_client.get(f"/api/agronomics/tomato/parameters/{name}").json()
        assert len(records) == 3
        for r in records:
            assert r["status"] == "sourced"
            assert r["source_id"] is not None
            assert r["stage_id"] is not None
            assert r["value_numeric"] is not None
            ctx = r["context"] or ""
            if "naturally ventilated polyhouse" in ctx:
                assert r["value_numeric"] == variants["polyhouse"]
            elif "shade-net" in ctx:
                assert r["value_numeric"] == variants["shade"]
            elif "open field" in ctx:
                assert r["value_numeric"] == variants["open field"]
            else:
                raise AssertionError(f"unrecognized Kc context: {ctx}")


def test_p_and_p2o5_remain_distinct(api_client):
    resp = api_client.get("/api/agronomics/tomato/parameters?domain=nutrient")
    assert resp.status_code == 200
    params = resp.json()
    names = {p["parameter_name"] for p in params}
    assert "p2o5_total_requirement_g_plant_season" in names
    assert not any(n == "p_total_requirement_g_plant_season" for n in names)
    p2o5 = next(p for p in params if p["parameter_name"] == "p2o5_total_requirement_g_plant_season")
    assert p2o5["value_text"] is not None  # per-hectare fact, not silently converted to per-plant
    assert p2o5["value_numeric"] is None

    # Phase 0 reference profile keeps soil P (element) and P2O5 demand as
    # separate fields -- confirm that separation still holds.
    day1 = api_client.get("/api/reference/tomato/day/1").json()
    assert "soil_p_mg_kg" in day1
    assert "p2o5_demand_g_plant_day" in day1
    assert day1["soil_p_mg_kg"] != day1["p2o5_demand_g_plant_day"]


def test_k_and_k2o_remain_distinct(api_client):
    resp = api_client.get("/api/agronomics/tomato/parameters?domain=nutrient")
    assert resp.status_code == 200
    names = {p["parameter_name"] for p in resp.json()}
    assert "k2o_total_requirement_g_plant_season" in names

    day1 = api_client.get("/api/reference/tomato/day/1").json()
    assert "soil_k_mg_kg" in day1
    assert "k2o_demand_g_plant_day" in day1
    assert day1["soil_k_mg_kg"] != day1["k2o_demand_g_plant_day"]


def test_stress_conditions_present_and_unsourced_thresholds_are_null(api_client):
    resp = api_client.get("/api/agronomics/tomato/stress-conditions")
    assert resp.status_code == 200
    conditions = resp.json()
    assert len(conditions) > 0
    stress_types = {c["stress_type"] for c in conditions}
    assert {
        "water_stress",
        "excessive_soil_moisture",
        "heat_stress",
        "humidity_stress",
        "nutrient_imbalance",
    } <= stress_types
    for c in conditions:
        if c["status"] != "sourced":
            assert c["threshold_value"] is None


def test_phase0_day_47_unchanged_after_phase1_5c(api_client):
    resp = api_client.get("/api/reference/tomato/day/47")
    assert resp.status_code == 200
    csv_row = {int(r["day"]): r for r in _load_csv_rows()}[47]
    body = resp.json()
    for col in EXPECTED_COLUMNS[1:]:
        assert body[col] == float(csv_row[col])


def test_phase0_day_120_unchanged_after_phase1_5c(api_client):
    resp = api_client.get("/api/reference/tomato/day/120")
    assert resp.status_code == 200
    csv_row = {int(r["day"]): r for r in _load_csv_rows()}[120]
    body = resp.json()
    for col in EXPECTED_COLUMNS[1:]:
        assert body[col] == float(csv_row[col])


def test_phase0_endpoints_still_work(api_client):
    assert api_client.get("/health").status_code == 200
    assert api_client.get("/api/reference/tomato").status_code == 200
    assert api_client.get("/api/reference/tomato/day/1").status_code == 200
    assert api_client.get("/api/reference/tomato/day/121").status_code == 404


def test_no_decision_engine_or_llm_modules_exist():
    """
    Phase 2 legitimately introduces a simulator (app/services/simulator/,
    app/models/simulation_*.py, app/routes/simulator.py) -- that's no
    longer forbidden. Still must not introduce a decision engine,
    optimizer, validator, or LLM/ML code. Guard this structurally: none
    of those modules should exist under app/.
    """
    from pathlib import Path

    app_dir = Path(__file__).resolve().parents[1] / "app"
    forbidden_name_fragments = [
        "optimizer",
        "decision_engine",
        "validator",
        "llm",
        "gemini",
    ]
    py_files = [p for p in app_dir.rglob("*.py")]
    offending = [
        str(p)
        for p in py_files
        if any(fragment in p.stem.lower() for fragment in forbidden_name_fragments)
    ]
    assert offending == [], f"Unexpected Phase 3+ modules found: {offending}"
