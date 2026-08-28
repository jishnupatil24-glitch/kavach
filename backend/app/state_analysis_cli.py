"""
WORKFLOW B -- presentation-only terminal front-end for Phase 3.
Contains ZERO trend/rate/persistence/ICAR/crop-stage calculation logic
of its own. It reads and formats an ALREADY-PERSISTED analysis via
app.services.state_analysis.history.get_stored_analysis -- it never
calls analyze_run() itself and is NOT responsible for creating the
persisted history during normal operation. Verified structurally by a
test that scans this module's source for calculation-logic fragments.

If nothing has been persisted yet for the requested run/day, this CLI
says so and stops -- it does not silently compute one on the fly. Use
`python -m app.services.state_analysis.history --run-id N` (Workflow A,
a separate backend step) to build/refresh that history first.

Usage:
    python -m app.state_analysis_cli --run-id 12
    python -m app.state_analysis_cli --run-id 12 --day 35
"""
from __future__ import annotations

import argparse
import sys

# Windows terminals commonly default to a legacy codepage that cannot
# encode the characters used below -- same fix as app/simulator_cli.py.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from app.database.session import Base, SessionLocal, engine
from app.services.state_analysis.history import get_stored_analysis
from app.services.state_analysis.service import ParameterAnalysis, StateAnalysis, StateAnalysisError

WIDTH = 70


def fail(message: str) -> None:
    print(f"✗ {message}")


def _fmt_current(pa: ParameterAnalysis) -> str:
    return f"{pa.current.value:.2f}{pa.icar.unit_suffix}"


def _fmt_rate(pa: ParameterAnalysis) -> str:
    trend = pa.trend
    if trend.rate_per_day is None:
        return "n/a (insufficient data)"
    return f"{trend.rate_per_day:+.2f} {trend.rate_unit}"


def _fmt_persistence_days(pa: ParameterAnalysis) -> str:
    days = pa.persistence.days
    if days is None:
        return "undetermined"
    return f"{days} day{'s' if days != 1 else ''}"


def _fmt_icar_row(pa: ParameterAnalysis) -> tuple[str, str, str]:
    icar = pa.icar
    current_str = f"{icar.current_value:.2f}{icar.unit_suffix}"
    if icar.icar_value is None:
        return current_str, "n/a", "n/a"
    ref_str = f"{icar.icar_value:.2f}{icar.unit_suffix}"
    diff_str = f"{icar.signed_difference:+.2f}{icar.unit_suffix}"
    return current_str, ref_str, diff_str


def print_analysis(analysis: StateAnalysis) -> None:
    print("=" * WIDTH)
    print("KAVACH -- PHASE 3 STATE ANALYSIS".center(WIDTH))
    print("=" * WIDTH)
    print()
    print(f"Simulation ID : {analysis.run_id}")
    print(f"Analysis Day  : {analysis.analysis_day}")
    print(f"Crop          : {analysis.crop.capitalize()}")

    print()
    print("-" * WIDTH)
    print("CURRENT STATE")
    print("-" * WIDTH)
    print()
    print(f"{'Parameter':<16}{'Current':<16}{'Trend':<14}{'Rate'}")
    print("-" * WIDTH)
    for pa in analysis.parameters:
        print(f"{pa.current.parameter:<16}{_fmt_current(pa):<16}{pa.trend.direction:<14}{_fmt_rate(pa)}")

    print()
    print("-" * WIDTH)
    print("TREND PERSISTENCE")
    print("-" * WIDTH)
    print()
    for pa in analysis.parameters:
        print(f"{pa.persistence.parameter:<16}{pa.persistence.direction:<14}{_fmt_persistence_days(pa)}")

    print()
    print("-" * WIDTH)
    print("ICAR REFERENCE COMPARISON")
    print("-" * WIDTH)
    print()
    print(f"{'Parameter':<16}{'Current':<16}{'ICAR':<16}{'Difference'}")
    print("-" * WIDTH)
    for pa in analysis.parameters:
        current_str, ref_str, diff_str = _fmt_icar_row(pa)
        print(f"{pa.icar.parameter:<16}{current_str:<16}{ref_str:<16}{diff_str}")
    icar_notes = [pa.icar.note for pa in analysis.parameters if pa.icar.note]
    if icar_notes:
        print()
        for note in dict.fromkeys(icar_notes):  # de-duplicate, preserve order
            print(f"  Note: {note}")

    print()
    print("-" * WIDTH)
    print("CROP-STAGE CONTEXT")
    print("-" * WIDTH)
    print()
    print(f"Current Day : {analysis.analysis_day}")
    if analysis.crop_stages:
        print("Applicable Stage(s):")
        for s in analysis.crop_stages:
            print(f"  - {s.name} (Day {s.start_day}-{s.end_day})")
        # full_cycle (Day 1-120) always matches alongside a Kc sub-stage --
        # that's expected multiplicity, not a source-data overlap. The
        # genuine ambiguity (day 100 only) is when more than one Kc
        # sub-stage itself matches, e.g. kc_mid_stage/kc_late_stage.
        sub_stage_matches = [s for s in analysis.crop_stages if s.name != "full_cycle"]
        if len(sub_stage_matches) > 1:
            print(
                f"  Note: the source-defined stage ranges overlap on day "
                f"{analysis.analysis_day} -- both are reported, not narrowed to one."
            )
    else:
        print(f"No day-resolvable crop stage found for day {analysis.analysis_day}.")

    print()
    print("-" * WIDTH)
    print("AGRONOMIC CONTEXT")
    print("-" * WIDTH)
    print()
    if analysis.agronomic_context:
        print(f"{'Parameter':<28}{'Value/Range':<16}{'Status':<18}{'Source ID'}")
        print("-" * WIDTH)
        for item in analysis.agronomic_context:
            unit_suffix = f" {item.unit}" if item.unit else ""
            value_col = f"{item.value_display}{unit_suffix}"
            source_col = str(item.source_id) if item.source_id is not None else "-"
            print(f"{item.parameter_name:<28}{value_col:<16}{item.status:<18}{source_col}")
            if item.context:
                print(f"    context: {item.context}")
    else:
        print(
            "No day-resolvable agronomic context available for this day "
            "(some agronomic parameters -- e.g. temperature thresholds -- "
            "are linked to crop stages that have no day mapping in the "
            "current agronomic knowledge base)."
        )

    print()
    print("-" * WIDTH)
    print("DATA QUALITY")
    print("-" * WIDTH)
    print()
    current_state_notes = list(dict.fromkeys(pa.current.note for pa in analysis.parameters if pa.current.note))
    all_notes = current_state_notes + analysis.data_quality_notes
    if all_notes:
        for note in all_notes:
            print(f"  - {note}")
    else:
        print("  No data-quality issues detected.")

    print()
    print("-" * WIDTH)
    print("STATE ANALYSIS SUMMARY")
    print("-" * WIDTH)
    print()
    for pa in analysis.parameters:
        print(f"• {pa.current.parameter} is {pa.trend.direction}.")

    moisture = next((pa for pa in analysis.parameters if pa.current.field == "soil_moisture_pct"), None)
    if moisture is not None and moisture.icar.icar_value is not None:
        direction_word = "above" if moisture.icar.signed_difference >= 0 else "below"
        print(
            f"• Current soil moisture is {moisture.icar.absolute_difference:.2f} "
            f"percentage points {direction_word} the ICAR reference."
        )

    if analysis.crop_stages:
        stage_names = ", ".join(s.name for s in analysis.crop_stages)
        print(f"• Current crop stage: {stage_names}.")

    for pa in analysis.parameters:
        if pa.persistence.days is not None:
            print(
                f"• {pa.current.parameter} trend has persisted for "
                f"{_fmt_persistence_days(pa)}."
            )

    print()
    print("=" * WIDTH)


def fetch_and_print(db, run_id: int, day: int | None) -> int:
    try:
        analysis = get_stored_analysis(db, run_id, day=day)
    except StateAnalysisError as e:
        fail(str(e))
        return 1

    if analysis is None:
        day_clause = f" at day {day}" if day is not None else ""
        fail(
            f"No persisted Phase 3 analysis found for simulation run {run_id}{day_clause}. "
            f"Run `python -m app.services.state_analysis.history --run-id {run_id}` "
            "first to build the backend history."
        )
        return 1

    print_analysis(analysis)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.state_analysis_cli",
        description="KAVACH Phase 3 state-analysis CLI",
    )
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--day", type=int, default=None)
    args = parser.parse_args(argv)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        return fetch_and_print(db, args.run_id, args.day)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
