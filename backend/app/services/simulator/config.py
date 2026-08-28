"""
SimulationConfig construction and validation. Kept separate from the
Pydantic API schema (app/schemas/simulator.py) so the simulator core has
no dependency on FastAPI/Pydantic -- it can be driven by tests or a
future non-HTTP caller identically.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.simulator import constants as C


class SimulationConfigError(ValueError):
    pass


@dataclass(frozen=True)
class SimulationConfig:
    duration_days: int
    scenario: str
    severity: str | None
    seed: int
    scenario_start_day: int | None
    scenario_duration_days: int | None


def build_config(
    duration_days: int,
    scenario: str,
    seed: int,
    severity: str | None = None,
    scenario_start_day: int | None = None,
    scenario_duration_days: int | None = None,
) -> SimulationConfig:
    if not (C.MIN_DURATION_DAYS <= duration_days <= C.MAX_DURATION_DAYS):
        raise SimulationConfigError(
            f"duration_days must be between {C.MIN_DURATION_DAYS} and "
            f"{C.MAX_DURATION_DAYS} (the ICAR-verified reference span) -- "
            f"got {duration_days}. The simulator does not extrapolate "
            f"past the ICAR reference period."
        )

    if scenario not in C.SCENARIOS:
        raise SimulationConfigError(f"scenario must be one of {C.SCENARIOS}, got {scenario!r}")

    if scenario == "normal":
        if severity is not None:
            raise SimulationConfigError("severity must be null when scenario is 'normal'")
        if scenario_start_day is not None or scenario_duration_days is not None:
            raise SimulationConfigError(
                "scenario_start_day/scenario_duration_days must be null when scenario is 'normal'"
            )
        return SimulationConfig(duration_days, scenario, None, seed, None, None)

    if severity not in C.SEVERITY_LEVELS:
        raise SimulationConfigError(f"severity must be one of {C.SEVERITY_LEVELS} for scenario {scenario!r}")

    if scenario_start_day is None or scenario_duration_days is None:
        raise SimulationConfigError(
            "scenario_start_day and scenario_duration_days are required when scenario is not 'normal'"
        )
    if not (1 <= scenario_start_day <= duration_days):
        raise SimulationConfigError("scenario_start_day must be within [1, duration_days]")
    if scenario_duration_days < 1:
        raise SimulationConfigError("scenario_duration_days must be >= 1")
    if scenario_start_day + scenario_duration_days - 1 > duration_days:
        raise SimulationConfigError(
            "scenario_start_day + scenario_duration_days - 1 must not exceed duration_days "
            "-- the scenario window cannot run past the requested simulation length"
        )

    return SimulationConfig(
        duration_days, scenario, severity, seed, scenario_start_day, scenario_duration_days
    )
