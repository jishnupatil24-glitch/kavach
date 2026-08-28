"""
Idempotent, ADDITIVE-ONLY insertion of Phase 5's two approved
project_defined decision-engine parameters into the EXISTING
agronomic_parameters table. Deliberately separate from
app.services.seed_agronomics.seed() (which deletes and reinserts the
WHOLE table) -- this script never deletes anything and never touches
any existing row, sourced or otherwise. Safe to run any number of
times: inserts a row only if one matching (crop, parameter_name,
status="project_defined") does not already exist.

    python -m app.services.decision_engine.seed_parameters
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
from app.models.simulation_run import SimulationRun  # noqa: F401 -- registers simulation_runs for decision_history's FK
from app.services.decision_engine.config_parameters import (
    DOMAIN_OPERATIONAL,
    PARAM_MIN_SEVERITY_FOR_ACTION,
    PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS,
    PROJECT_DEFINED_DISCLAIMER,
    STATUS_PROJECT_DEFINED,
)

TOMATO = "tomato"


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


def ensure_decision_engine_parameters(db: Session) -> int:
    """
    Returns the number of rows actually inserted (0, 1, or 2).
    Approved values (see design-approval history):
      - min_severity_for_action = "MODERATE"
      - tier2_min_abnormal_duration_days_for_action = 5 days
    Both: crop="tomato", domain="operational", status="project_defined",
    source_id=NULL (not externally sourced), notes carry the exact
    approved disclaimer verbatim.
    """
    inserted = 0

    if not _row_exists(db, TOMATO, PARAM_MIN_SEVERITY_FOR_ACTION):
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=PARAM_MIN_SEVERITY_FOR_ACTION,
                value_text="MODERATE",
                unit=None,
                stage_id=None,
                context="Phase 5 decision-engine eligibility gate -- minimum Phase 4 severity band required before a category is considered for an action recommendation.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=PROJECT_DEFINED_DISCLAIMER,
            )
        )
        inserted += 1

    if not _row_exists(db, TOMATO, PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS):
        db.add(
            AgronomicParameter(
                crop=TOMATO,
                domain=DOMAIN_OPERATIONAL,
                parameter_name=PARAM_TIER2_MIN_ABNORMAL_DURATION_DAYS,
                value_numeric=5,
                unit="days",
                stage_id=None,
                context="Phase 5 decision-engine eligibility gate -- minimum abnormal_state_duration.days required, for Tier-2 (ICAR-sign+trend-proxy) categories only, before a category is considered for an action recommendation.",
                status=STATUS_PROJECT_DEFINED,
                source_id=None,
                notes=PROJECT_DEFINED_DISCLAIMER,
            )
        )
        inserted += 1

    if inserted:
        db.commit()
    return inserted


def main(argv: list[str] | None = None) -> int:
    # Pulls in every route module, which transitively imports every
    # SQLAlchemy model (simulation_runs, agronomic_sources, etc.) --
    # required before create_all() below, since several FKs here are
    # resolved by table name, not a direct Python import in this file
    # (same reasoning as tests/conftest.py's own seeded_db fixture).
    from app import main as _main  # noqa: F401

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        count = ensure_decision_engine_parameters(db)
        print(f"OK: inserted {count} new project_defined decision-engine parameter row(s) (0 means already present).")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
