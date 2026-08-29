/**
 * The 7 sensor variables KAVACH analyses, and how each maps across the three
 * real endpoints:
 *   - analysis:     parameters[].current.field   (Phase 3)
 *   - observations: SensorObservationOut key     (Phase 2, raw)
 *   - reference:    TomatoReferenceProfileOut key (Phase 0, ICAR)
 *
 * Trend charts plot the daily mean of raw observations against the ICAR
 * reference series. That is real data, clearly labelled as "daily mean of
 * sensor readings" — no fabricated analysed time series.
 */
import type { SensorObservation, TomatoReferenceProfile } from '@/api/types';

export interface VariableDef {
  key: string; // canonical id, matches analysis field name
  plain: string;
  short: string;
  unit: string;
  observationKey: keyof SensorObservation;
  referenceKey: keyof TomatoReferenceProfile;
  headline: boolean; // shown in the Farm State headline row
  precision: number;
}

export const VARIABLES: VariableDef[] = [
  {
    key: 'soil_moisture_pct',
    plain: 'Soil moisture',
    short: 'Moisture',
    unit: '%',
    observationKey: 'soil_moisture_pct',
    referenceKey: 'soil_moisture_pct',
    headline: true,
    precision: 1,
  },
  {
    key: 'temperature_c',
    plain: 'Temperature',
    short: 'Temp',
    unit: '°C',
    observationKey: 'temperature_c',
    referenceKey: 'temperature_c',
    headline: true,
    precision: 1,
  },
  {
    key: 'humidity_pct',
    plain: 'Humidity',
    short: 'Humidity',
    unit: '%',
    observationKey: 'humidity_pct',
    referenceKey: 'humidity_pct',
    headline: true,
    precision: 1,
  },
  {
    key: 'daily_dli_mol_m2_day',
    plain: 'Light (DLI)',
    short: 'Light',
    unit: 'mol/m²/day',
    observationKey: 'daily_dli_mol_m2_day',
    referenceKey: 'dli_mol_m2_day',
    headline: false,
    precision: 1,
  },
  {
    key: 'soil_n_mg_kg',
    plain: 'Soil nitrogen',
    short: 'Nitrogen',
    unit: 'mg/kg',
    observationKey: 'soil_n_mg_kg',
    referenceKey: 'soil_n_mg_kg',
    headline: false,
    precision: 0,
  },
  {
    key: 'soil_p_mg_kg',
    plain: 'Soil phosphorus',
    short: 'Phosphorus',
    unit: 'mg/kg',
    observationKey: 'soil_p_mg_kg',
    referenceKey: 'soil_p_mg_kg',
    headline: false,
    precision: 0,
  },
  {
    key: 'soil_k_mg_kg',
    plain: 'Soil potassium',
    short: 'Potassium',
    unit: 'mg/kg',
    observationKey: 'soil_k_mg_kg',
    referenceKey: 'soil_k_mg_kg',
    headline: false,
    precision: 0,
  },
];

export function variableByField(field: string | null | undefined): VariableDef | undefined {
  if (!field) return undefined;
  return (
    VARIABLES.find((v) => v.key === field) ||
    VARIABLES.find((v) => v.observationKey === field || v.referenceKey === field)
  );
}
