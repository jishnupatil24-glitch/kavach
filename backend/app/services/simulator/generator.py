"""
Orchestrates full observation generation for one simulation config.

Soil moisture is the one genuinely STATEFUL variable: it is carried as
one continuous running value across the whole simulation, anchored to
the real ICAR value only once (day 1, hour 0) -- never hard-reset on
later days. This is what lets a multi-day scenario (e.g. water_shortage)
produce a compounding effect instead of "healing" every midnight.

Day d's calibrated irrigation total (see calibration.py) was derived to
bridge ICAR day d's moisture to ICAR day d+1's moisture. It is therefore
split into 4 equal shares and applied to the 4 transitions that
ORIGINATE from day d's own 4 slots:

    day d hour0 -> day d hour6      (share 1, day d's calibration)
    day d hour6 -> day d hour12     (share 2, day d's calibration)
    day d hour12 -> day d hour18    (share 3, day d's calibration)
    day d hour18 -> day (d+1) hour0 (share 4, day d's calibration --
                                      lands on day d+1's reading, but is
                                      still charged to day d's total)

Getting this ownership backwards (charging the transition landing on day
d's hour-0 reading to day d's OWN calibration instead of day d-1's) would
front-load an entire day's irrigation into that same day's own readings
-- which is exactly wrong whenever ICAR shows a same-day jump the next
day (e.g. a fertigation-like event): the simulated day would overshoot
before the jump was supposed to appear at all. This was caught by the
approved requirement's own sanity check (day 28's calibrated irrigation
bridges to day 29's real +3-point moisture jump; it must show up on day
29, not inflate day 28).

Scenario multipliers (water_shortage, excess_irrigation) scale the
OWNING day's share, exactly as in the calibration table -- heatwave and
high_humidity leave irrigation untouched and act only through
temperature/humidity (which affects evaporative loss, computed live at
the ARRIVING slot's own generated conditions).

Edge case: the LAST simulated day's 4th share (the transition that would
land on day duration_days+1's hour 0) has no arriving slot to apply to,
since generation stops there -- that day loses 1 of its 4 shares. This
affects only the final day of any run and is a documented
simplification, not a bug.

Temperature/humidity/N/P/K are computed independently per slot (not
part of this irrigation bookkeeping) and each draw noise from an
independently seeded stream (see rng.py) so noise never correlates
across variables.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.services.simulator import causal_model as CM
from app.services.simulator import constants as C
from app.services.simulator import scenarios as S
from app.services.simulator.baseline import BaselineDay
from app.services.simulator.calibration import build_calibrated_irrigation_table
from app.services.simulator.rng import bounded_gaussian, make_stream
from app.services.simulator.scenarios import SimulationConfig


@dataclass(frozen=True)
class GeneratedSlot:
    day: int
    hour: int
    temperature_c: float
    humidity_pct: float
    soil_moisture_pct: float
    daily_dli_mol_m2_day: float
    soil_n_mg_kg: float
    soil_p_mg_kg: float
    soil_k_mg_kg: float
    # internal/debug fields, not part of the sensor-facing shape
    irrigation_input_pct: float
    evaporative_loss_pct: float
    temperature_delta_from_scenario: float
    humidity_delta_from_scenario: float


def _lerp(a: float, b: float, fraction: float) -> float:
    return a + (b - a) * fraction


def generate(config: SimulationConfig, baseline: dict[int, BaselineDay]) -> list[GeneratedSlot]:
    temp_rng = make_stream(config.seed, "temperature")
    humidity_rng = make_stream(config.seed, "humidity")
    moisture_rng = make_stream(config.seed, "moisture")
    n_rng = make_stream(config.seed, "soil_n")
    p_rng = make_stream(config.seed, "soil_p")
    k_rng = make_stream(config.seed, "soil_k")

    calibrated_irrigation = build_calibrated_irrigation_table(baseline)

    n_slots = config.duration_days * 4
    slot_day = [(i // 4) + 1 for i in range(n_slots)]
    slot_hour = [(0, 6, 12, 18)[i % 4] for i in range(n_slots)]

    temperature: list[float] = [0.0] * n_slots
    humidity: list[float] = [0.0] * n_slots
    evap: list[float] = [0.0] * n_slots
    temp_delta_log: list[float] = [0.0] * n_slots
    humidity_delta_log: list[float] = [0.0] * n_slots

    for i in range(n_slots):
        day, hour = slot_day[i], slot_hour[i]
        today = baseline[day]
        temp_delta = S.temperature_delta_c(day, config)
        humidity_delta = S.humidity_delta_pct(day, config)

        temp_noise = bounded_gaussian(temp_rng, C.NOISE_STDDEV_TEMPERATURE_C, C.NOISE_CLIP_STDDEVS)
        t = today.temperature_c + CM.diurnal_temperature_offset(hour) + temp_delta + temp_noise

        humidity_noise = bounded_gaussian(humidity_rng, C.NOISE_STDDEV_HUMIDITY_PCT, C.NOISE_CLIP_STDDEVS)
        h_raw = CM.humidity_from_temperature_deviation(today.humidity_pct, t - today.temperature_c) \
            + humidity_delta + humidity_noise
        h = CM.clamp(h_raw, C.HUMIDITY_FLOOR_PCT, C.HUMIDITY_CEILING_PCT)

        temperature[i] = t
        humidity[i] = h
        evap[i] = CM.evaporative_loss_pct(t, h)
        temp_delta_log[i] = temp_delta
        humidity_delta_log[i] = humidity_delta

    # `true_moisture` evolves deterministically (evap + irrigation only,
    # NO noise fed back into it) -- it is the running state consumed by
    # the NEXT transition's math. `moisture` (the reported/observed
    # value) adds a small independent noise draw on top for sensor-like
    # texture, but that noise is never re-injected into the state.
    #
    # This distinction matters: soil moisture is an INTEGRATOR (each
    # step depends on the previous one). Adding noise directly into an
    # integrator turns it into a random walk whose drift grows with
    # sqrt(number of steps) -- for a 60+ day run that produced multi-point
    # unbounded-looking drift for some seeds, defeating the whole point
    # of the NORMAL-scenario calibration. Reported-only noise gives the
    # same sensor-like texture without that compounding drift.
    true_moisture: list[float] = [0.0] * n_slots
    moisture: list[float] = [0.0] * n_slots
    irrigation_log: list[float] = [0.0] * n_slots
    true_moisture[0] = baseline[1].soil_moisture_pct  # single real-data anchor
    moisture[0] = true_moisture[0]
    evap[0] = 0.0  # not applied to anything -- no transition produced slot 0

    for i in range(1, n_slots):
        owning_day = slot_day[i - 1]  # the FROM-slot's day owns this transition's irrigation share
        share = (calibrated_irrigation[owning_day] * S.irrigation_multiplier(owning_day, config)) / 4.0
        true_moisture[i] = CM.clamp(
            true_moisture[i - 1] - evap[i] + share,
            C.SOIL_MOISTURE_FLOOR_PCT,
            C.SOIL_MOISTURE_CEILING_PCT,
        )
        moisture_noise = bounded_gaussian(moisture_rng, C.NOISE_STDDEV_MOISTURE_PCT, C.NOISE_CLIP_STDDEVS)
        moisture[i] = CM.clamp(
            true_moisture[i] + moisture_noise,
            C.SOIL_MOISTURE_FLOOR_PCT,
            C.SOIL_MOISTURE_CEILING_PCT,
        )
        irrigation_log[i] = share

    slots: list[GeneratedSlot] = []
    for i in range(n_slots):
        day, hour = slot_day[i], slot_hour[i]
        today = baseline[day]
        tomorrow = baseline.get(day + 1, today)  # holds flat only at the absolute last ICAR day (120)
        fraction = hour / 24.0

        n_value = _lerp(today.soil_n_mg_kg, tomorrow.soil_n_mg_kg, fraction) + bounded_gaussian(
            n_rng, C.NOISE_STDDEV_SOIL_N_MG_KG, C.NOISE_CLIP_STDDEVS
        )
        p_value = _lerp(today.soil_p_mg_kg, tomorrow.soil_p_mg_kg, fraction) + bounded_gaussian(
            p_rng, C.NOISE_STDDEV_SOIL_P_MG_KG, C.NOISE_CLIP_STDDEVS
        )
        k_value = _lerp(today.soil_k_mg_kg, tomorrow.soil_k_mg_kg, fraction) + bounded_gaussian(
            k_rng, C.NOISE_STDDEV_SOIL_K_MG_KG, C.NOISE_CLIP_STDDEVS
        )

        slots.append(
            GeneratedSlot(
                day=day,
                hour=hour,
                temperature_c=temperature[i],
                humidity_pct=humidity[i],
                soil_moisture_pct=moisture[i],
                daily_dli_mol_m2_day=today.dli_mol_m2_day,
                soil_n_mg_kg=n_value,
                soil_p_mg_kg=p_value,
                soil_k_mg_kg=k_value,
                irrigation_input_pct=irrigation_log[i],
                evaporative_loss_pct=evap[i],
                temperature_delta_from_scenario=temp_delta_log[i],
                humidity_delta_from_scenario=humidity_delta_log[i],
            )
        )

    return slots
