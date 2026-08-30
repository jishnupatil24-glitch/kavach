"""
Idempotent, ADDITIVE-ONLY insertion of Phase 6's approved project_defined
optimization parameters into the EXISTING agronomic_parameters table.
Mirrors app.services.decision_engine.seed_parameters exactly: never
deletes/updates any existing row, safe to run any number of times.

    python -m app.services.optimization.seed_parameters
"""
from __future__ import annotations

import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from sqlalchemy.orm import Session

from app.database.session import Base, SessionLocal, engine
from app.models.agronomic_parameter import AgronomicParameter
from app.models.crop_stage import CropStage
from app.models.simulation_run import SimulationRun  # noqa: F401 -- registers simulation_runs for FKs
from app.services.optimization.config_parameters import (
    DOMAIN_OPERATIONAL,
    IRRIGATION_EFFICIENCY_PARAM_BY_SYSTEM_TYPE,
    PARAM_BASELINE_IRRIGATION_KC_INITIAL,
    PARAM_BASELINE_IRRIGATION_KC_LATE,
    PARAM_BASELINE_IRRIGATION_KC_MID,
    PARAM_IRRIGATION_EFFICIENCY_UNKNOWN_DEFAULT,
    PARAM_REVIEW_CYCLE_DAYS,
    PARAM_TYPICAL_APPLICATION_MULTIPLIER_PCT,
    PROJECT_DEFINED_DISCLAIMER,
    STATUS_PROJECT_DEFINED,
)

TOMATO = "tomato"

_BASELINE_IRRIGATION_ROWS = [
    (PARAM_BASELINE_IRRIGATION_KC_INITIAL, "kc_initial_stage", 1.5,
     "Commonly-cited drip-polyhouse tomato vegetative-stage water use (~1-2 L/plant/day) "
     "repeated across agri-extension literature -- not derived from KAVACH's own Kc x ETo "
     "chain (eto_reference_mm_day remains status=derived, value NULL)."),
    (PARAM_BASELINE_IRRIGATION_KC_MID, "kc_mid_stage", 3.5,
     "Peak flowering/fruiting demand, commonly cited 3-5 L/plant/day. Same Kc x ETo caveat as above."),
    (PARAM_BASELINE_IRRIGATION_KC_LATE, "kc_late_stage", 2.5,
     "Reduced late/ripening demand. Same Kc x ETo caveat as above."),
]

_IRRIGATION_ADJUSTMENT_ROWS = [
    ("irrigation_adjustment_pct_low", 10.0),
    ("irrigation_adjustment_pct_moderate", 20.0),
    ("irrigation_adjustment_pct_high", 30.0),
    ("irrigation_adjustment_pct_critical", 40.0),
]
_IRRIGATION_ADJUSTMENT_CONTEXT = (
    "Linear mapping onto Phase 4's own SEVERITY_ORDER (0-3) ordinal scale x 10%. No sourced "
    "dose-response curve for tomato irrigation correction magnitude exists -- a deliberately "
    "simple, testable heuristic, not a fitted agronomic model."
)

_NUTRIENT_ADJUSTMENT_ROWS = [
    ("nutrient_adjustment_pct_low", 10.0),
    ("nutrient_adjustment_pct_moderate", 20.0),
    ("nutrient_adjustment_pct_high", 30.0),
    ("nutrient_adjustment_pct_critical", 40.0),
]
_NUTRIENT_ADJUSTMENT_CONTEXT = (
    "Same ordinal heuristic as irrigation_adjustment_pct_*, applied to the sourced ICAR "
    "per-plant-per-day N/P/K demand baseline instead of a project-defined baseline."
)

_IRRIGATION_EFFICIENCY_ROWS = [
    ("irrigation_efficiency_drip_pct", 85.0, "drip"),
    ("irrigation_efficiency_sprinkler_pct", 70.0, "sprinkler"),
    ("irrigation_efficiency_flood_pct", 50.0, "flood"),
    (PARAM_IRRIGATION_EFFICIENCY_UNKNOWN_DEFAULT, 75.0, "unspecified/unrecognized system"),
]
_IRRIGATION_EFFICIENCY_CONTEXT = (
    "Commonly-cited agricultural-extension efficiency range midpoint -- not tied to one "
    "verified KAVACH source."
)

_TYPICAL_APPLICATION_CONTEXT = (
    "KAVACH's value proposition is precise irrigation vs. common over-application without "
    "decision support. No sourced/measured dataset of this project's own farmer irrigation "
    "behavior exists, so this is a flat, deliberately simple prototype heuristic (same spirit "
    "as irrigation_adjustment_pct_*) used only as a comparison point for the 'typical "
    "application' figure shown alongside KAVACH's recommendation -- it never changes "
    "baseline_l_per_plant_day (theoretical requirement) or optimized_l_per_plant_day (KAVACH's "
    "recommendation)."
)


def _row_exists(db: Session, crop: str, parameter_name: str) -> bool:
    return (
        db.query(AgronomicParameter)
        .filter(
            AgronomicParameter.crop == crop,
            AgronomicParameter.parameter_name == parameter_name,
            AgronomicParameter.status == STATUS_PROJECT_DEFINED,
        )
        .first()
        is not None
    )


def _stage_id(db: Session, crop: str, stage_name: str) -> int | None:
    row = db.query(CropStage).filter(CropStage.crop == crop, CropStage.name == stage_name).first()
    return row.id if row is not None else None


def ensure_optimization_parameters(db: Session) -> int:
    """
    Returns the number of rows actually inserted. Approved values (see
    Phase 6 design-approval history):
      - baseline_irrigation_kc_{initial,mid,late}_l_per_plant_day = 1.5/3.5/2.5
      - irrigation_adjustment_pct_{low,moderate,high,critical} = 10/20/30/40
      - nutrient_adjustment_pct_{low,moderate,high,critical} = 10/20/30/40
      - irrigation_review_cycle_days = 3
      - irrigation_efficiency_{drip,sprinkler,flood,unknown_default}_pct = 85/70/50/75
      - typical_application_multiplier_pct = 40
    All: crop="tomato", domain="operational", status="project_defined",
    source_id=NULL, notes carry PROJECT_DEFINED_DISCLAIMER verbatim.
    """
    inserted = 0

    for parameter_name, stage_name, value, rationale in _BASELINE_IRRIGATION_ROWS:
        if _row_exists(db, TOMATO, parameter_name):
            continue
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=parameter_name,
                value_numeric=value,
                unit="L/plant/day",
                stage_id=_stage_id(db, TOMATO, stage_name),
                context=f"Phase 6 prototype irrigation baseline (theoretical crop water requirement) for {stage_name}.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=f"{PROJECT_DEFINED_DISCLAIMER} {rationale}",
            )
        )
        inserted += 1

    for parameter_name, value in _IRRIGATION_ADJUSTMENT_ROWS:
        if _row_exists(db, TOMATO, parameter_name):
            continue
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=parameter_name,
                value_numeric=value,
                unit="%",
                stage_id=None,
                context="Phase 6 irrigation quantity adjustment magnitude, keyed by Phase 4 severity band.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=f"{PROJECT_DEFINED_DISCLAIMER} {_IRRIGATION_ADJUSTMENT_CONTEXT}",
            )
        )
        inserted += 1

    for parameter_name, value in _NUTRIENT_ADJUSTMENT_ROWS:
        if _row_exists(db, TOMATO, parameter_name):
            continue
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=parameter_name,
                value_numeric=value,
                unit="%",
                stage_id=None,
                context="Phase 6 N/P/K quantity adjustment magnitude, keyed by Phase 4 severity band.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=f"{PROJECT_DEFINED_DISCLAIMER} {_NUTRIENT_ADJUSTMENT_CONTEXT}",
            )
        )
        inserted += 1

    if not _row_exists(db, TOMATO, PARAM_REVIEW_CYCLE_DAYS):
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=PARAM_REVIEW_CYCLE_DAYS,
                value_numeric=3,
                unit="days",
                stage_id=None,
                context="Phase 6 operational re-evaluation cadence for a recommended quantitative action.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=(
                    f"{PROJECT_DEFINED_DISCLAIMER} A review/intervention cycle, NOT a claim that crop "
                    "physiology recovers in exactly this many days -- no soil-moisture-response physics "
                    "model exists (field capacity / permanent wilting point remain context_dependent, NULL)."
                ),
            )
        )
        inserted += 1

    for parameter_name, value, label in _IRRIGATION_EFFICIENCY_ROWS:
        if _row_exists(db, TOMATO, parameter_name):
            continue
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=parameter_name,
                value_numeric=value,
                unit="%",
                stage_id=None,
                context=f"Phase 6 irrigation delivery efficiency assumption for {label}.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=f"{PROJECT_DEFINED_DISCLAIMER} {_IRRIGATION_EFFICIENCY_CONTEXT}",
            )
        )
        inserted += 1

    if not _row_exists(db, TOMATO, PARAM_TYPICAL_APPLICATION_MULTIPLIER_PCT):
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=PARAM_TYPICAL_APPLICATION_MULTIPLIER_PCT,
                value_numeric=40.0,
                unit="%",
                stage_id=None,
                context=(
                    "Phase 6 prototype comparison point: how much MORE water a farmer typically "
                    "applies than the theoretical crop requirement, absent decision support."
                ),
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=f"{PROJECT_DEFINED_DISCLAIMER} {_TYPICAL_APPLICATION_CONTEXT}",
            )
        )
        inserted += 1

    if inserted:
        db.commit()
    return inserted


def main(argv: list[str] | None = None) -> int:
    from app import main as _main  # noqa: F401 -- registers every model before create_all()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = ensure_optimization_parameters(db)
        print(f"OK: inserted {count} new project_defined optimization parameter row(s) (0 means already present).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
