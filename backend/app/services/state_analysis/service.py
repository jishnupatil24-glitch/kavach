"""
Phase 3 orchestrator. `analyze_run()` is the single entrypoint both the
CLI (app/state_analysis_cli.py) and the API (app/routes/state_analysis.py)
call -- neither may duplicate the calculation logic in this module or
its sibling modules (enforced structurally by
tests/test_state_analysis.py).

Deliberately reads only: SensorObservation (Phase 2, unmodified),
SimulationRun (Phase 2, unmodified), the Phase 0 ICAR baseline loader,
and CropStage/AgronomicParameter (Phase 1/1.5C, unmodified). Never
imports the simulator's internal per-slot debug/traceability table, or
any app.services.simulator module other than baseline -- this is what
keeps the analysis reusable against a future real-sensor feed, not
just simulator output.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.sensor_observation import SensorObservation
from app.models.simulation_run import SimulationRun
from app.services.simulator.baseline import load_baseline
from app.services.state_analysis.crop_stage_context import (
    AgronomicContextItem,
    StageMatch,
    resolve_agronomic_context,
    resolve_crop_stages,
)
from app.services.state_analysis.current_state import CurrentState, compute_current_state
from app.services.state_analysis.daily_aggregation import aggregate_daily
from app.services.state_analysis.icar_deviation import IcarDeviation, compute_icar_deviation
from app.services.state_analysis.parameters import PARAMETERS
from app.services.state_analysis.persistence import PersistenceResult, compute_persistence
from app.services.state_analysis.trend import TrendResult, compute_trend


class StateAnalysisError(ValueError):
    pass


class RunNotFoundError(StateAnalysisError):
    pass


class InvalidDayError(StateAnalysisError):
    pass


@dataclass(frozen=True)
class ParameterAnalysis:
    current: CurrentState
    trend: TrendResult
    persistence: PersistenceResult
    icar: IcarDeviation


@dataclass(frozen=True)
class StateAnalysis:
    run_id: int
    crop: str
    analysis_day: int
    duration_days: int
    parameters: list[ParameterAnalysis]
    crop_stages: list[StageMatch]
    agronomic_context: list[AgronomicContextItem]
    data_quality_notes: list[str]


_PERCENTAGE_FIELDS = [("humidity_pct", "Humidity"), ("soil_moisture_pct", "Soil Moisture")]
"""
Out-of-range flagging is restricted to fields whose physical range
(0-100%) is a mathematical certainty, not an agronomic judgment call --
flagging e.g. an "implausible" temperature would require an externally
chosen agronomic threshold, which this phase does not invent.
"""


def _data_quality_notes(observations: list[SensorObservation], analysis_day: int) -> list[str]:
    notes: list[str] = []

    by_day: dict[int, list[SensorObservation]] = {}
    for o in observations:
        by_day.setdefault(o.day, []).append(o)

    expected_days = set(range(1, analysis_day + 1))
    present_days = set(by_day)
    missing_days = sorted(expected_days - present_days)
    if missing_days:
        notes.append(f"No observations at all for day(s): {missing_days}.")

    for day in sorted(present_days):
        hours = sorted(o.hour for o in by_day[day])
        if len(hours) < 4:
            notes.append(
                f"Day {day}: only {len(hours)} of 4 expected 6-hour observations present (hours present: {hours})."
            )

    for field, label in _PERCENTAGE_FIELDS:
        for o in observations:
            value = getattr(o, field)
            if value is not None and not (0.0 <= value <= 100.0):
                notes.append(
                    f"{label} on day {o.day} hour {o.hour:02d}:00 = {value:.2f}% -- "
                    "outside the physically possible 0-100% range."
                )

    return notes


def analyze_run(db: Session, run_id: int, day: int | None = None) -> StateAnalysis:
    run = db.query(SimulationRun).filter(SimulationRun.id == run_id).first()
    if run is None:
        raise RunNotFoundError(f"No simulation run found with id {run_id}")

    if day is not None and not (1 <= day <= run.duration_days):
        raise InvalidDayError(
            f"day must be between 1 and {run.duration_days} for simulation run {run_id}"
        )
    upper_bound = day if day is not None else run.duration_days

    observations = (
        db.query(SensorObservation)
        .filter(SensorObservation.simulation_run_id == run_id, SensorObservation.day <= upper_bound)
        .order_by(SensorObservation.day, SensorObservation.hour)
        .all()
    )
    if not observations:
        raise InvalidDayError(
            f"No observations found for simulation run {run_id} up to day {upper_bound}"
        )

    analysis_day = observations[-1].day
    baseline = load_baseline(db)

    parameter_analyses: list[ParameterAnalysis] = []
    aggregation_notes: list[str] = []
    for spec in PARAMETERS:
        daily_values = aggregate_daily(observations, spec.field)
        # `observations` is non-empty here (checked above) and every
        # SensorObservation column is non-nullable today, so every
        # field has at least one reading on at least one day --
        # daily_values is therefore never empty in practice. A future
        # nullable real-sensor field could violate that; this is not
        # guarded further here, matching this module's existing
        # tolerance for that same assumption elsewhere.

        current = compute_current_state(daily_values, spec)

        # Trend/rate/persistence operate on ONE point per day (the
        # daily aggregate), never on the day's 4 raw 6-hour readings --
        # treating those 4 as 4 separate "days" would fabricate a
        # trend out of pure within-day noise.
        trend_points = [(float(dv.day), dv.value) for dv in daily_values]
        trend = compute_trend(spec.label, trend_points, spec.rate_unit)

        persistence_points = [(dv.day, dv.value) for dv in daily_values]
        persistence = compute_persistence(spec.label, persistence_points, trend.direction, trend.stable_band)

        icar = compute_icar_deviation(
            spec.label, current.value, current.day, spec.baseline_field, baseline, spec.current_suffix
        )

        parameter_analyses.append(ParameterAnalysis(current, trend, persistence, icar))

        for dv in daily_values:
            if dv.note:
                aggregation_notes.append(dv.note)

    crop_stages = resolve_crop_stages(db, run.crop, analysis_day)
    agronomic_context = resolve_agronomic_context(db, run.crop, [s.stage_id for s in crop_stages])
    data_quality_notes = _data_quality_notes(observations, analysis_day) + aggregation_notes

    return StateAnalysis(
        run_id=run.id,
        crop=run.crop,
        analysis_day=analysis_day,
        duration_days=run.duration_days,
        parameters=parameter_analyses,
        crop_stages=crop_stages,
        agronomic_context=agronomic_context,
        data_quality_notes=data_quality_notes,
    )
