"""
WORKFLOW B -- presentation-only terminal front-end for Phase 4.
Contains ZERO evidence/gate/detection/severity logic of its own. It
reads and formats ALREADY-PERSISTED/ALREADY-STORED data via:
  - app.services.stress_assessment.history.get_stored_assessment
    (Phase 4's own persisted history -- never calls assess_run())
  - app.services.state_analysis.history.get_stored_analysis
    (Phase 3's own persisted history, --show-pipeline mode only --
    never calls analyze_run())
  - a direct read-only query of SensorObservation (Phase 2's raw
    readings, --show-pipeline mode only -- never touches Phase 2's
    generation code, never writes)
Not responsible for creating any persisted history during normal
operation. Verified structurally by a test that scans this module's
source for detection/calculation-logic fragments.

If nothing has been persisted yet for the requested run/day, this CLI
says so and stops -- it does not silently compute one on the fly. Use
`python -m app.services.stress_assessment.history --run-id N`
(Workflow A, a separate backend step) to build/refresh that history
first -- though under the automatic pipeline (run_service.create_run),
this should already exist for every run created through the normal
path.

Usage:
    python -m app.stress_assessment_cli --run-id 12
    python -m app.stress_assessment_cli --run-id 12 --day 35
    python -m app.stress_assessment_cli --run-id 12 --day 35 --show-pipeline
"""
from __future__ import annotations

import argparse
import sys

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from app.database.session import Base, SessionLocal, engine
from app.models.sensor_observation import SensorObservation
from app.services.state_analysis.history import get_stored_analysis
from app.services.state_analysis.parameters import PARAMETERS
from app.services.state_analysis.service import StateAnalysis, StateAnalysisError
from app.services.stress_assessment.evidence import SEVERITY_DISCLAIMER
from app.services.stress_assessment.history import get_stored_assessment
from app.services.stress_assessment.service import StressAssessment

WIDTH = 78

_SUFFIX_BY_FIELD = {spec.field: spec.current_suffix for spec in PARAMETERS}
_LABEL_BY_FIELD = {spec.field: spec.label for spec in PARAMETERS}


def fail(message: str) -> None:
    print(f"✗ {message}")


def _fmt_value(field: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f}{_SUFFIX_BY_FIELD.get(field, '')}"


def _fmt_rate(problem) -> str:
    if problem.rate_per_day is None:
        return "n/a"
    return f"{problem.rate_per_day:+.2f} {problem.rate_unit}"


def _fmt_persistence(problem) -> str:
    if problem.persistence_days is None:
        return "n/a"
    return f"{problem.persistence_days} day{'s' if problem.persistence_days != 1 else ''}"


def _fmt_abnormal_duration(problem) -> str:
    days = problem.abnormal_state_duration.days
    if days is None:
        return "n/a"
    return f"{days} day{'s' if days != 1 else ''}"


def _fmt_deviation(problem) -> str:
    if problem.icar_deviation is None:
        return "n/a"
    suffix = _SUFFIX_BY_FIELD.get(problem.field, "")
    return f"{problem.icar_deviation:+.2f}{suffix}"


def print_raw_sensor_readings(observations: list[SensorObservation], day: int) -> None:
    print("-" * WIDTH)
    print("PHASE 2 -- RAW SENSOR READINGS (read-only, unmodified)")
    print("-" * WIDTH)
    print()
    print(f"Day {day}")
    print(f"{'Hour':<6}{'Temp °C':<10}{'Humidity %':<12}{'Moisture %':<12}{'N':<8}{'P':<8}{'K':<8}{'DLI'}")
    print("-" * WIDTH)
    for o in sorted(observations, key=lambda r: r.hour):
        print(
            f"{o.hour:02d}:00 "
            f"{o.temperature_c:<9.2f} {o.humidity_pct:<11.2f} {o.soil_moisture_pct:<11.2f} "
            f"{o.soil_n_mg_kg:<7.1f} {o.soil_p_mg_kg:<7.1f} {o.soil_k_mg_kg:<7.1f} "
            f"{o.daily_dli_mol_m2_day:.2f}"
        )
    if not observations:
        print("  (no raw observations found for this day)")


def print_phase3_state(state: StateAnalysis) -> None:
    print("-" * WIDTH)
    print("PHASE 3 -- STATE ANALYSIS (from stored state_analysis_history, unmodified)")
    print("-" * WIDTH)
    print()
    for pa in state.parameters:
        label = _LABEL_BY_FIELD.get(pa.current.field, pa.current.field)
        suffix = _SUFFIX_BY_FIELD.get(pa.current.field, "")
        rate = f"{pa.trend.rate_per_day:+.2f} {pa.trend.rate_unit}" if pa.trend.rate_per_day is not None else "n/a"
        persistence = f"{pa.persistence.days} day{'s' if pa.persistence.days != 1 else ''}" if pa.persistence.days is not None else "n/a"
        deviation = f"{pa.icar.signed_difference:+.2f}{suffix}" if pa.icar.signed_difference is not None else "n/a"
        print(f"{label}:")
        print(f"  Current       : {pa.current.value:.2f}{suffix}")
        print(f"  Trend         : {pa.trend.direction}")
        print(f"  Rate          : {rate}")
        print(f"  Trend Persistence: {persistence}")
        print(f"  ICAR deviation: {deviation}")
        print()
    if state.crop_stages:
        print("Crop stage:")
        for s in state.crop_stages:
            print(f"  - {s.name} (Day {s.start_day}-{s.end_day})")
    if state.agronomic_context:
        print("Agronomic context:")
        for item in state.agronomic_context:
            print(f"  - {item.parameter_name}: {item.value_display} [{item.status}]")


def print_assessment(assessment: StressAssessment, show_header: bool = True) -> None:
    if show_header:
        print("=" * WIDTH)
        print("KAVACH -- PHASE 4 PROBLEM ASSESSMENT".center(WIDTH))
        print("=" * WIDTH)
        print()
        print(f"Simulation ID  : {assessment.run_id}")
        print(f"Assessment Day : {assessment.assessment_day}")
        print(f"Crop           : {assessment.crop.capitalize()}")
    else:
        print("-" * WIDTH)
        print("PHASE 4 -- PROBLEM ASSESSMENT + EVIDENCE + SEVERITY")

    print()
    print("-" * WIDTH)
    print("CROP-STAGE CONTEXT")
    print("-" * WIDTH)
    print()
    if assessment.crop_stages:
        for s in assessment.crop_stages:
            print(f"  - {s.name} (Day {s.start_day}-{s.end_day})")
    else:
        print(f"  No day-resolvable crop stage found for day {assessment.assessment_day}.")

    print()
    print("-" * WIDTH)
    print("PROBLEM ASSESSMENTS (all 10 categories -- kept for auditability)")
    print("-" * WIDTH)
    print()
    print(f"{'Category':<22}{'Status':<22}{'Severity':<20}{'Direction':<12}{'Current'}")
    print("-" * WIDTH)
    for p in assessment.problems:
        print(
            f"{p.label:<22}{p.status:<22}{p.severity:<20}{p.direction:<12}"
            f"{_fmt_value(p.field, p.current_value)}"
        )
    print()
    print(f"Note: {SEVERITY_DISCLAIMER}")

    print()
    print("-" * WIDTH)
    print("EVIDENCE DETAIL (categories at weak_evidence or above)")
    print("-" * WIDTH)
    print()
    evidenced = assessment.evidenced_problems()
    if not evidenced:
        print("  None -- no category reached the evidence bar on this day.")
    for p in evidenced:
        print(f"[{p.label}] status: {p.status}   severity: {p.severity}")
        print(
            f"    Current: {_fmt_value(p.field, p.current_value)}   "
            f"ICAR: {_fmt_value(p.field, p.icar_value)}   "
            f"Deviation: {_fmt_deviation(p)}"
        )
        print(f"    Trend: {p.direction}   Rate: {_fmt_rate(p)}   Trend Persistence: {_fmt_persistence(p)}")
        ad = p.abnormal_state_duration
        print(
            f"    Abnormal-State Duration: {_fmt_abnormal_duration(p)}   "
            f"(tier: {ad.tier})"
        )
        print(f"    Abnormal-State Duration note: {ad.provenance_note}")
        if p.severity_factors is not None:
            f = p.severity_factors
            intensity_display = f"{f.intensity_ratio:.2f}" if f.intensity_ratio is not None else "n/a (zero noise floor)"
            print(
                f"    Severity factors: deviation_ratio={f.deviation_ratio:.3f} (score {f.deviation_score}), "
                f"intensity_ratio={intensity_display} (score {f.intensity_score}), "
                f"duration_fraction={f.duration_fraction:.3f} (score {f.duration_score}) "
                f"-> total {f.total_score}/6"
            )
        for note in p.sourced_corroboration_notes:
            print(f"    Sourced corroboration: {note}")
        for note in p.provenance_notes:
            print(f"    Provenance note: {note}")
        if p.raw_range is not None:
            r = p.raw_range
            suffix = _SUFFIX_BY_FIELD.get(p.field, "")
            print(
                f"    Today's raw 6-hour range: {r.min_value:.2f}{suffix} - "
                f"{r.max_value:.2f}{suffix} ({r.n_readings} readings) -- {r.label}"
            )
        print()

    print("-" * WIDTH)
    print("PHASE 5 CANDIDATE PROBLEMS (weak_evidence or above)")
    print("-" * WIDTH)
    print()
    if evidenced:
        for p in evidenced:
            print(f"  - {p.label} ({p.status}, {p.severity})")
    else:
        print("  None.")

    print()
    print("=" * WIDTH)


def fetch_and_print(db, run_id: int, day: int | None, show_pipeline: bool = False) -> int:
    try:
        assessment = get_stored_assessment(db, run_id, day=day)
    except StateAnalysisError as e:
        fail(str(e))
        return 1

    if assessment is None:
        day_clause = f" at day {day}" if day is not None else ""
        fail(
            f"No persisted Phase 4 assessment found for simulation run {run_id}{day_clause}. "
            f"Run `python -m app.services.stress_assessment.history --run-id {run_id}` "
            "first to build the backend history."
        )
        return 1

    if not show_pipeline:
        print_assessment(assessment)
        return 0

    # --show-pipeline: read-only presentation of all three layers.
    # Nothing below computes, writes, or duplicates any calculation --
    # each read reuses the same stored data the normal (non-pipeline)
    # mode already reads.
    phase3_state = get_stored_analysis(db, run_id, day=assessment.assessment_day)
    raw_observations = (
        db.query(SensorObservation)
        .filter(
            SensorObservation.simulation_run_id == run_id,
            SensorObservation.day == assessment.assessment_day,
        )
        .all()
    )

    print("=" * WIDTH)
    print("KAVACH -- PHASE 2 -> PHASE 3 -> PHASE 4 PIPELINE".center(WIDTH))
    print("=" * WIDTH)
    print()
    print("SIMULATION")
    print(f"Simulation ID : {assessment.run_id}")
    print(f"Analysis Day  : {assessment.assessment_day}")
    print(f"Crop          : {assessment.crop.capitalize()}")
    print()

    print_raw_sensor_readings(raw_observations, assessment.assessment_day)
    print()

    if phase3_state is not None:
        print_phase3_state(phase3_state)
    else:
        print("-" * WIDTH)
        print("PHASE 3 -- STATE ANALYSIS")
        print("-" * WIDTH)
        print("  (no persisted Phase 3 history found for this run/day)")
    print()

    print_assessment(assessment, show_header=False)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.stress_assessment_cli",
        description="KAVACH Phase 4 problem/stress-assessment CLI",
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--day", type=int, default=None)
    parser.add_argument(
        "--show-pipeline", action="store_true",
        help="Show the full Phase 2 raw readings -> Phase 3 state -> Phase 4 assessment chain (read-only).",
    )
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return fetch_and_print(db, args.run_id, args.day, show_pipeline=args.show_pipeline)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
