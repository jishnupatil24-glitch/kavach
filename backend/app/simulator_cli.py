"""
Hackathon-friendly command-line interface for the Phase 2 virtual
sensor simulator.

This file contains ZERO simulation logic of its own. It only:
  - collects input from the terminal,
  - calls the EXISTING simulator service (app.services.simulator.*),
  - formats the EXISTING SensorObservation rows as terminal tables.

Usage:
    python -m app.simulator_cli                    interactive: generate a run, view basic results
    python -m app.simulator_cli --run-id 7 --day 35 view one day of an existing run
"""
from __future__ import annotations

import argparse
import sys

# Windows terminals (cmd.exe / PowerShell) commonly default to a legacy
# codepage (e.g. cp1252) that cannot encode the checkmark/box-drawing
# characters used below, which would otherwise crash mid-output with a
# UnicodeEncodeError. Force UTF-8 on stdout/stderr so the CLI never
# crashes on its own output, regardless of the host console's codepage.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

from app.database.session import Base, SessionLocal, engine
from app.models.sensor_observation import SensorObservation
from app.models.simulation_run import SimulationRun
from app.services.simulator.config import SimulationConfigError, build_config
from app.services.simulator.constants import SCENARIOS, SEVERITY_LEVELS
from app.services.simulator.run_service import create_run

BANNER = (
    "=============================================\n"
    "       KAVACH VIRTUAL SENSOR SIMULATOR\n"
    "============================================="
)

SCENARIO_MENU = [
    ("normal", "normal"),
    ("heatwave", "heatwave"),
    ("water_shortage", "water_shortage"),
    ("excess_irrigation", "excess_irrigation"),
    ("high_humidity", "high_humidity"),
]
SEVERITY_MENU = ["mild", "moderate", "severe"]

COLUMNS = [
    ("Day", "day", 4),
    ("Time", "time", 6),
    ("Temp°C", "temperature_c", 7),
    ("Humidity", "humidity_pct", 9),
    ("Soil Moist", "soil_moisture_pct", 11),
    ("DLI", "daily_dli_mol_m2_day", 6),
    ("Soil N", "soil_n_mg_kg", 8),
    ("Soil P", "soil_p_mg_kg", 8),
    ("Soil K", "soil_k_mg_kg", 8),
]


def fail(message: str) -> None:
    print(f"✗ {message}")


def ok(message: str) -> None:
    print(f"✓ {message}")


# --------------------------------------------------------------------
# input helpers -- reprompt on bad input, never a stack trace
# --------------------------------------------------------------------

def prompt_int(label: str, min_value: int | None = None, max_value: int | None = None) -> int:
    while True:
        raw = input(f"{label}\n> ").strip()
        try:
            value = int(raw)
        except ValueError:
            fail("Please enter a whole number.")
            continue
        if min_value is not None and value < min_value or max_value is not None and value > max_value:
            bound = f"{min_value}" if max_value is None else f"{min_value} and {max_value}"
            fail(f"Value must be between {bound}.")
            continue
        return value


def prompt_menu(label: str, options: list[str]) -> str:
    while True:
        print(f"\n{label}")
        for i, opt in enumerate(options, start=1):
            print(f"{i}. {opt}")
        raw = input("> ").strip()
        try:
            index = int(raw)
        except ValueError:
            fail("Please enter the number shown next to your choice.")
            continue
        if not (1 <= index <= len(options)):
            fail(f"Please enter a number from 1 to {len(options)}.")
            continue
        return options[index - 1]


# --------------------------------------------------------------------
# table rendering
# --------------------------------------------------------------------

def _fmt_cell(observation: SensorObservation, key: str) -> str:
    if key == "day":
        return str(observation.day)
    if key == "time":
        return f"{observation.hour:02d}:00"
    if key in ("humidity_pct", "soil_moisture_pct"):
        return f"{getattr(observation, key):.2f}%"
    return f"{getattr(observation, key):.2f}"


def render_table(observations: list[SensorObservation]) -> str:
    widths = [max(w, len(header)) for header, _, w in COLUMNS]
    for obs in observations:
        for i, (_, key, _) in enumerate(COLUMNS):
            widths[i] = max(widths[i], len(_fmt_cell(obs, key)))

    def border(left: str, mid: str, right: str) -> str:
        return left + mid.join("─" * (w + 2) for w in widths) + right

    def row(cells: list[str]) -> str:
        return "│" + "│".join(f" {c:<{w}} " for c, w in zip(cells, widths)) + "│"

    lines = [border("┌", "┬", "┐")]
    lines.append(row([h for h, _, _ in COLUMNS]))
    lines.append(border("├", "┼", "┤"))
    for obs in observations:
        lines.append(row([_fmt_cell(obs, key) for _, key, _ in COLUMNS]))
    lines.append(border("└", "┴", "┘"))
    return "\n".join(lines)


def print_full_dataset(run: SimulationRun, observations: list[SensorObservation]) -> None:
    """Prints every day's table, in chronological order. No day is skipped."""
    print(f"\nKAVACH — SIMULATION #{run.id}")
    print(f"Scenario: {run.scenario}")
    print(f"Duration: {run.duration_days} days")
    print(f"Observations: {len(observations)}")

    by_day: dict[int, list[SensorObservation]] = {}
    for obs in observations:
        by_day.setdefault(obs.day, []).append(obs)

    for day in range(1, run.duration_days + 1):
        print(f"\n---------------- DAY {day} ----------------")
        print(render_table(by_day[day]))


def print_summary(run: SimulationRun, observations: list[SensorObservation]) -> None:
    temps = [o.temperature_c for o in observations]
    moistures = [o.soil_moisture_pct for o in observations]

    print("\n========================================")
    print("SIMULATION SUMMARY")
    print("========================================\n")
    print(f"Simulation ID: {run.id}")
    print(f"Duration: {run.duration_days} days")
    print(f"Observations: {len(observations)}")
    print(f"Scenario: {run.scenario}")
    if run.scenario_start_day is not None:
        window_end = run.scenario_start_day + run.scenario_duration_days - 1
        print(f"Scenario window: Day {run.scenario_start_day}–{window_end}")
    if run.severity is not None:
        print(f"Severity: {run.severity}")
    print(f"Seed: {run.seed}")

    print("\nTemperature:")
    print(f"  Min:     {min(temps):.2f}°C")
    print(f"  Max:     {max(temps):.2f}°C")
    print(f"  Average: {sum(temps) / len(temps):.2f}°C")
    print("\nSoil Moisture:")
    print(f"  Min:     {min(moistures):.2f}%")
    print(f"  Max:     {max(moistures):.2f}%")
    print(f"  Average: {sum(moistures) / len(moistures):.2f}%")
    print("\n========================================")


def fetch_observations(db, run_id: int, day: int | None = None) -> list[SensorObservation]:
    query = db.query(SensorObservation).filter(SensorObservation.simulation_run_id == run_id)
    if day is not None:
        query = query.filter(SensorObservation.day == day)
    return query.order_by(SensorObservation.day, SensorObservation.hour).all()


# --------------------------------------------------------------------
# modes
# --------------------------------------------------------------------

def run_view_day(run_id: int, day: int) -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
        if run is None:
            fail(f"No simulation found with ID {run_id}.")
            return 1
        if not (1 <= day <= run.duration_days):
            fail(f"Day must be between 1 and {run.duration_days} for simulation #{run_id}.")
            return 1

        observations = fetch_observations(db, run_id, day=day)
        print(f"\nKAVACH — Simulation #{run_id} — Day {day}\n")
        print(render_table(observations))
        return 0
    finally:
        db.close()


def run_interactive_generate() -> int:
    print(BANNER)
    print()

    duration_days = prompt_int("How many days do you want to simulate?", 1, 120)
    scenario = prompt_menu("Scenario:", [name for name, _ in SCENARIO_MENU])

    severity = None
    scenario_start_day = None
    scenario_duration_days = None
    if scenario != "normal":
        scenario_start_day = prompt_int("\nScenario start day:", 1, duration_days)
        scenario_duration_days = prompt_int(
            "\nScenario duration:", 1, duration_days - scenario_start_day + 1
        )
        severity = prompt_menu("Severity:", SEVERITY_MENU)

    seed = prompt_int("\nSeed:", None, None)

    print("\nGenerating...")

    try:
        config = build_config(
            duration_days=duration_days,
            scenario=scenario,
            seed=seed,
            severity=severity,
            scenario_start_day=scenario_start_day,
            scenario_duration_days=scenario_duration_days,
        )
    except SimulationConfigError as e:
        fail(str(e))
        return 1

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        try:
            run = create_run(db, config)
        except Exception:
            fail(
                "Could not generate the simulation. Is the reference data "
                "seeded? Run `python -m app.services.seed_database` first."
            )
            return 1

        observations = fetch_observations(db, run.id)

        ok("Simulation created and stored in database")

        print_full_dataset(run, observations)
        print_summary(run, observations)

        print(
            f"\nTip: view a single day again later with:\n"
            f"  python -m app.simulator_cli --run-id {run.id} --day <day>"
        )
        return 0
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m app.simulator_cli",
        description="KAVACH virtual sensor simulator CLI",
    )
    parser.add_argument("--run-id", type=int, default=None)
    parser.add_argument("--day", type=int, default=None)
    args = parser.parse_args(argv)

    if args.run_id is not None and args.day is not None:
        return run_view_day(args.run_id, args.day)
    if args.run_id is not None or args.day is not None:
        fail("Both --run-id and --day are required together.")
        return 1

    try:
        return run_interactive_generate()
    except (KeyboardInterrupt, EOFError):
        print()
        fail("Cancelled.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
