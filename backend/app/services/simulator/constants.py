"""
Every constant in this file is a MODEL ASSUMPTION: a simulator-internal
number chosen to produce plausible, causally-consistent virtual-sensor
data. None of them are agricultural facts, none have a source_id, and
none should ever be confused with the sourced values in
`agronomic_parameters`. They exist to make the simplified simulator
model behave sensibly, not to represent verified agronomy.
"""

# MODEL ASSUMPTION: spread between a day's coolest (00:00) and warmest
# (12:00) synthetic temperature reading around that day's ICAR daily
# anchor. ICAR gives one temperature per day; a real polyhouse has a
# day/night swing that must exist for 6-hour resolution to mean
# anything, but no source gives us this specific figure.
# Unit: degrees C. Allowed range: 0-10 (0 disables the diurnal shape).
DIURNAL_TEMPERATURE_AMPLITUDE_C = 3.0

# MODEL ASSUMPTION: how much humidity moves opposite to a temperature
# deviation from that day's ICAR baseline (hotter air holds relatively
# less moisture at similar absolute humidity -- standard physical
# direction, not a sourced coefficient).
# Unit: %RH per degree C. Allowed range: 0-5 (0 disables coupling).
TEMP_HUMIDITY_COUPLING_COEFFICIENT = 1.5

# MODEL ASSUMPTION: simplified evaporative/transpirational soil-moisture
# loss per 6-hour slot, as a function of temperature and humidity. This
# is NOT FAO-56 Penman-Monteith ETo -- it exists only to make "hotter
# and drier -> faster moisture decline" true inside the simulator.
# base: %/6h at a notional reference condition (20C, 60% RH).
# temp_sensitivity: extra %/6h lost per degree C above 20C.
# humidity_sensitivity: %/6h loss reduced per %RH above 60%.
# All three configurable; evap is clipped to [0, EVAP_MAX_PCT_PER_6H].
EVAP_BASE_RATE_PCT_PER_6H = 0.8
EVAP_TEMP_SENSITIVITY_PCT_PER_6H_PER_C = 0.06
EVAP_HUMIDITY_SENSITIVITY_PCT_PER_6H_PER_PCT = 0.03
EVAP_MAX_PCT_PER_6H = 5.0

# MODEL ASSUMPTION: hard bound on the NORMAL-scenario calibrated daily
# irrigation input (see calibration.py). Keeps the calibration
# "physically reasonable" per the approved requirement -- when the ICAR
# trajectory would imply an irrigation value outside this bound, the
# calibration clamps rather than forcing an exact match (see
# calibration.py docstring).
# Unit: % soil-moisture-equivalent per day. Allowed range: 0-30.
MAX_DAILY_IRRIGATION_PCT = 15.0

# MODEL ASSUMPTION: numeric safety bounds only -- NOT the sourced
# field-capacity / permanent-wilting-point values, which remain
# `context_dependent`/unresolved in `agronomic_parameters` (Phase
# 1.5C). These just stop the simplified model producing <0% or >100%.
SOIL_MOISTURE_FLOOR_PCT = 0.0
SOIL_MOISTURE_CEILING_PCT = 100.0
HUMIDITY_FLOOR_PCT = 0.0
HUMIDITY_CEILING_PCT = 100.0

# MODEL ASSUMPTION: magnitude of small bounded random perturbation added
# per variable per slot, for sensor-like texture without swamping the
# causal signal. Each variable's noise is drawn from an independently
# seeded stream (see rng.py) so noise never accidentally correlates
# across variables.
NOISE_STDDEV_TEMPERATURE_C = 0.4
NOISE_STDDEV_HUMIDITY_PCT = 1.0
NOISE_STDDEV_MOISTURE_PCT = 0.3
NOISE_STDDEV_SOIL_N_MG_KG = 0.5
NOISE_STDDEV_SOIL_P_MG_KG = 0.2
NOISE_STDDEV_SOIL_K_MG_KG = 0.8
NOISE_CLIP_STDDEVS = 2.5  # clip noise draws to +-2.5 standard deviations

# MODEL ASSUMPTION: per-severity temperature forcing added during a
# heatwave window. Unit: degrees C.
HEATWAVE_TEMP_DELTA_C = {"mild": 2.0, "moderate": 4.0, "severe": 7.0}

# MODEL ASSUMPTION: fraction of the NORMAL-calibrated daily irrigation
# actually delivered during a water-shortage window. Unitless fraction.
WATER_SHORTAGE_IRRIGATION_MULTIPLIER = {"mild": 0.5, "moderate": 0.25, "severe": 0.0}

# MODEL ASSUMPTION: multiplier on the NORMAL-calibrated daily irrigation
# during an excess-irrigation window. Unitless fraction.
EXCESS_IRRIGATION_MULTIPLIER = {"mild": 1.5, "moderate": 2.0, "severe": 3.0}

# MODEL ASSUMPTION: per-severity humidity forcing added during a
# high-humidity window (narratively: reduced ventilation). Unit: %RH.
HIGH_HUMIDITY_DELTA_PCT = {"mild": 7.0, "moderate": 12.0, "severe": 20.0}

SEVERITY_LEVELS = ("mild", "moderate", "severe")
SCENARIOS = ("normal", "heatwave", "water_shortage", "excess_irrigation", "high_humidity")

MIN_DURATION_DAYS = 1
MAX_DURATION_DAYS = 120  # hard cap at the ICAR-verified span; no extrapolation past it
