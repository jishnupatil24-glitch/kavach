"""
Farm configuration WRITE/SETTER workflow -- deliberately separate from
the read-only Phase 6 CLI (app.optimization_cli). Persistent per
simulation run, upsertable (unlike the append-only convention every
other Phase 2-5 table follows): farm configuration is corrective input
a farmer can update, not a measurement.

    python -m app.services.optimization.farm_config --run-id 584 \
        --field-area 1 --field-area-unit acre --plant-population 8000
"""
from __future__ import annotations

import argparse
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from sqlalchemy.orm import Session

from app.database.session import Base, SessionLocal, engine
from app.models.farm_configuration import FarmConfiguration
from app.models.simulation_run import SimulationRun
from app.services.optimization.units import UnsupportedAreaUnitError, area_to_m2


class RunNotFoundError(Exception):
    pass


_UPSERTABLE_OPTIONAL_FIELDS = (
    "plant_population", "plant_spacing_m", "row_spacing_m", "cultivar",
    "irrigation_system_type", "irrigation_efficiency_pct",
    "available_water_l_per_day", "pump_capacity_l_per_hour", "pump_power_kw",
    "water_cost_per_liter", "fertilizer_cost_per_kg_n",
    "fertilizer_cost_per_kg_p2o5", "fertilizer_cost_per_kg_k2o",
)


def get_farm_configuration(db: Session, run_id: int) -> FarmConfiguration | None:
    return db.query(FarmConfiguration).filter(FarmConfiguration.simulation_run_id == run_id).first()


def upsert_farm_configuration(
    db: Session,
    run_id: int,
    crop: str | None = None,
    field_area: float | None = None,
    field_area_unit: str | None = None,
    **optional_fields,
) -> FarmConfiguration:
    """
    Upsert by simulation_run_id. On first creation, field_area and
    field_area_unit are required (crop defaults to the run's own crop
    if not explicitly given -- that's a real existing fact, not a
    guess). On update, only the fields explicitly passed (non-None)
    are changed; anything omitted keeps its existing stored value.
    field_area_unit is validated immediately (fail fast on an unknown
    unit, never silently interpreted).
    """
    unknown_fields = set(optional_fields) - set(_UPSERTABLE_OPTIONAL_FIELDS)
    if unknown_fields:
        raise TypeError(f"Unknown farm configuration field(s): {sorted(unknown_fields)}")

    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    if field_area_unit is not None:
        area_to_m2(1.0, field_area_unit)  # raises UnsupportedAreaUnitError if invalid

    existing = get_farm_configuration(db, run_id)

    if existing is None:
        if field_area is None or field_area_unit is None:
            raise ValueError(
                "field_area and field_area_unit are required to create a new farm "
                f"configuration for run {run_id} (none exists yet)."
            )
        existing = FarmConfiguration(
            simulation_run_id=run_id,
            crop=crop if crop is not None else run.crop,
            field_area=field_area,
            field_area_unit=field_area_unit,
        )
        for name in _UPSERTABLE_OPTIONAL_FIELDS:
            value = optional_fields.get(name)
            if value is not None:
                setattr(existing, name, value)
        db.add(existing)
    else:
        if crop is not None:
            existing.crop = crop
        if field_area is not None:
            existing.field_area = field_area
        if field_area_unit is not None:
            existing.field_area_unit = field_area_unit
        for name in _UPSERTABLE_OPTIONAL_FIELDS:
            value = optional_fields.get(name)
            if value is not None:
                setattr(existing, name, value)

    db.commit()
    db.refresh(existing)
    return existing


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.services.optimization.farm_config",
        description="KAVACH Phase 6 farm configuration setter (write/upsert, persistent per simulation run).",
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--crop", type=str, default=None)
    parser.add_argument("--field-area", type=float, default=None)
    parser.add_argument("--field-area-unit", type=str, default=None)
    parser.add_argument("--plant-population", type=int, default=None)
    parser.add_argument("--plant-spacing-m", type=float, default=None)
    parser.add_argument("--row-spacing-m", type=float, default=None)
    parser.add_argument("--cultivar", type=str, default=None)
    parser.add_argument("--irrigation-system-type", type=str, default=None)
    parser.add_argument("--irrigation-efficiency-pct", type=float, default=None)
    parser.add_argument("--available-water-l-per-day", type=float, default=None)
    parser.add_argument("--pump-capacity-l-per-hour", type=float, default=None)
    parser.add_argument("--pump-power-kw", type=float, default=None)
    parser.add_argument("--water-cost-per-liter", type=float, default=None)
    parser.add_argument("--fertilizer-cost-per-kg-n", type=float, default=None)
    parser.add_argument("--fertilizer-cost-per-kg-p2o5", type=float, default=None)
    parser.add_argument("--fertilizer-cost-per-kg-k2o", type=float, default=None)
    args = parser.parse_args(argv)

    optional_fields = {
        "plant_population": args.plant_population,
        "plant_spacing_m": args.plant_spacing_m,
        "row_spacing_m": args.row_spacing_m,
        "cultivar": args.cultivar,
        "irrigation_system_type": args.irrigation_system_type,
        "irrigation_efficiency_pct": args.irrigation_efficiency_pct,
        "available_water_l_per_day": args.available_water_l_per_day,
        "pump_capacity_l_per_hour": args.pump_capacity_l_per_hour,
        "pump_power_kw": args.pump_power_kw,
        "water_cost_per_liter": args.water_cost_per_liter,
        "fertilizer_cost_per_kg_n": args.fertilizer_cost_per_kg_n,
        "fertilizer_cost_per_kg_p2o5": args.fertilizer_cost_per_kg_p2o5,
        "fertilizer_cost_per_kg_k2o": args.fertilizer_cost_per_kg_k2o,
    }

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            config = upsert_farm_configuration(
                db, args.run_id, crop=args.crop,
                field_area=args.field_area, field_area_unit=args.field_area_unit,
                **optional_fields,
            )
        except (RunNotFoundError, ValueError, UnsupportedAreaUnitError, TypeError) as e:
            print(f"✗ {e}")
            return 1
        print(f"✓ Farm configuration saved for simulation run {args.run_id}:")
        print(f"    crop={config.crop}  field_area={config.field_area} {config.field_area_unit}")
        print(f"    plant_population={config.plant_population}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
