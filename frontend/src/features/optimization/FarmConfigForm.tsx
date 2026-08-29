import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { FarmConfiguration, FarmConfigurationIn, FieldAreaUnit } from '@/api/types';
import { useSaveFarmConfig } from '@/api/hooks/optimization';
import { Button } from '@/components/primitives/Button';
import { ErrorState } from '@/components/primitives/states';

const UNITS: FieldAreaUnit[] = ['acre', 'hectare', 'm2'];

type FormState = Record<string, string>;

function toState(cfg: FarmConfiguration | undefined): FormState {
  const s: FormState = {};
  const keys = [
    'field_area',
    'field_area_unit',
    'plant_population',
    'plant_spacing_m',
    'row_spacing_m',
    'cultivar',
    'irrigation_system_type',
    'irrigation_efficiency_pct',
    'available_water_l_per_day',
    'pump_capacity_l_per_hour',
    'pump_power_kw',
    'water_cost_per_liter',
    'fertilizer_cost_per_kg_n',
    'fertilizer_cost_per_kg_p2o5',
    'fertilizer_cost_per_kg_k2o',
  ] as const;
  for (const k of keys) {
    const v = cfg?.[k as keyof FarmConfiguration];
    s[k] = v == null ? '' : String(v);
  }
  if (!s.field_area_unit) s.field_area_unit = 'acre';
  return s;
}

const NUMERIC = new Set([
  'field_area',
  'plant_population',
  'plant_spacing_m',
  'row_spacing_m',
  'irrigation_efficiency_pct',
  'available_water_l_per_day',
  'pump_capacity_l_per_hour',
  'pump_power_kw',
  'water_cost_per_liter',
  'fertilizer_cost_per_kg_n',
  'fertilizer_cost_per_kg_p2o5',
  'fertilizer_cost_per_kg_k2o',
]);

export function FarmConfigForm({
  runId,
  current,
  onSaved,
}: {
  runId: number;
  current: FarmConfiguration | undefined;
  onSaved: () => void;
}) {
  const save = useSaveFarmConfig(runId);
  const [form, setForm] = useState<FormState>(() => toState(current));

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const errors = useMemo(() => {
    const e: Record<string, string> = {};
    if (!form.field_area || Number(form.field_area) <= 0)
      e.field_area = 'Field area is required and must be greater than 0.';
    if (!UNITS.includes(form.field_area_unit as FieldAreaUnit))
      e.field_area_unit = 'Choose acre, hectare or m².';
    for (const k of NUMERIC) {
      if (form[k] !== '' && Number.isNaN(Number(form[k]))) e[k] = 'Must be a number.';
    }
    return e;
  }, [form]);

  const valid = Object.keys(errors).length === 0;

  const submit = () => {
    if (!valid) return;
    const body: FarmConfigurationIn = {};
    for (const [k, v] of Object.entries(form)) {
      if (v === '') continue;
      (body as Record<string, unknown>)[k] = NUMERIC.has(k) ? Number(v) : v;
    }
    save.mutate(body, { onSuccess: onSaved });
  };

  return (
    <form
      className="space-y-8"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <Group title="Field">
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            id="fc-area"
            label="Field area"
            required
            value={form.field_area}
            onChange={(v) => set('field_area', v)}
            error={errors.field_area}
          />
          <SelectField
            id="fc-unit"
            label="Area unit"
            required
            value={form.field_area_unit}
            onChange={(v) => set('field_area_unit', v)}
            error={errors.field_area_unit}
            options={UNITS.map((u) => ({ value: u, label: u === 'm2' ? 'm²' : u }))}
          />
          <NumberField
            id="fc-pop"
            label="Plant population"
            hint="Set this to unlock whole-field water and nutrient totals."
            value={form.plant_population}
            onChange={(v) => set('plant_population', v)}
            error={errors.plant_population}
          />
          <TextField
            id="fc-cultivar"
            label="Cultivar"
            value={form.cultivar}
            onChange={(v) => set('cultivar', v)}
          />
          <NumberField
            id="fc-ps"
            label="Plant spacing (m)"
            hint="Used to estimate population if you don't enter one."
            value={form.plant_spacing_m}
            onChange={(v) => set('plant_spacing_m', v)}
            error={errors.plant_spacing_m}
          />
          <NumberField
            id="fc-rs"
            label="Row spacing (m)"
            value={form.row_spacing_m}
            onChange={(v) => set('row_spacing_m', v)}
            error={errors.row_spacing_m}
          />
        </div>
      </Group>

      <Group title="Irrigation">
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField
            id="fc-sys"
            label="Irrigation system"
            hint="e.g. drip, sprinkler, furrow — sets a default efficiency."
            value={form.irrigation_system_type}
            onChange={(v) => set('irrigation_system_type', v)}
          />
          <NumberField
            id="fc-eff"
            label="Irrigation efficiency (%)"
            value={form.irrigation_efficiency_pct}
            onChange={(v) => set('irrigation_efficiency_pct', v)}
            error={errors.irrigation_efficiency_pct}
          />
          <NumberField
            id="fc-water"
            label="Available water (L/day)"
            hint="Enables the water-supply feasibility check."
            value={form.available_water_l_per_day}
            onChange={(v) => set('available_water_l_per_day', v)}
            error={errors.available_water_l_per_day}
          />
          <NumberField
            id="fc-pump"
            label="Pump capacity (L/hour)"
            hint="Enables the pump-capacity feasibility check."
            value={form.pump_capacity_l_per_hour}
            onChange={(v) => set('pump_capacity_l_per_hour', v)}
            error={errors.pump_capacity_l_per_hour}
          />
          <NumberField
            id="fc-kw"
            label="Pump power (kW)"
            value={form.pump_power_kw}
            onChange={(v) => set('pump_power_kw', v)}
            error={errors.pump_power_kw}
          />
        </div>
      </Group>

      <Group title="Costs">
        <div className="grid gap-4 sm:grid-cols-2">
          <NumberField
            id="fc-wcost"
            label="Water cost (per litre)"
            hint="Enables a water cost figure."
            value={form.water_cost_per_liter}
            onChange={(v) => set('water_cost_per_liter', v)}
            error={errors.water_cost_per_liter}
          />
          <NumberField
            id="fc-ncost"
            label="Fertiliser cost — N (per kg)"
            value={form.fertilizer_cost_per_kg_n}
            onChange={(v) => set('fertilizer_cost_per_kg_n', v)}
            error={errors.fertilizer_cost_per_kg_n}
          />
          <NumberField
            id="fc-pcost"
            label="Fertiliser cost — P₂O₅ (per kg)"
            value={form.fertilizer_cost_per_kg_p2o5}
            onChange={(v) => set('fertilizer_cost_per_kg_p2o5', v)}
            error={errors.fertilizer_cost_per_kg_p2o5}
          />
          <NumberField
            id="fc-kcost"
            label="Fertiliser cost — K₂O (per kg)"
            value={form.fertilizer_cost_per_kg_k2o}
            onChange={(v) => set('fertilizer_cost_per_kg_k2o', v)}
            error={errors.fertilizer_cost_per_kg_k2o}
          />
        </div>
      </Group>

      {save.isError ? <ErrorState error={save.error} /> : null}

      <div className="flex items-center justify-end gap-3">
        <Button type="submit" variant="primary" disabled={!valid || save.isPending}>
          {save.isPending ? 'Saving…' : 'Save configuration'}
        </Button>
      </div>
    </form>
  );
}

function Group({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset>
      <legend className="mb-3 font-sans text-sm font-semibold text-ink">{title}</legend>
      {children}
    </fieldset>
  );
}

interface FieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  error?: string;
  hint?: string;
  required?: boolean;
}

function FieldShell({
  id,
  label,
  error,
  hint,
  required,
  children,
}: FieldProps & { children: ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="mb-1 block font-sans text-sm font-medium text-ink">
        {label}
        {required ? <span className="text-sev-high"> *</span> : null}
      </label>
      {children}
      {hint ? (
        <p id={`${id}-hint`} className="mt-1 text-xs text-muted">
          {hint}
        </p>
      ) : null}
      {error ? (
        <p id={`${id}-error`} role="alert" className="mt-1 text-xs text-sev-high">
          {error}
        </p>
      ) : null}
    </div>
  );
}

function NumberField(props: FieldProps) {
  return (
    <FieldShell {...props}>
      <input
        id={props.id}
        type="number"
        step="any"
        inputMode="decimal"
        className="input"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        aria-describedby={
          [props.hint ? `${props.id}-hint` : null, props.error ? `${props.id}-error` : null]
            .filter(Boolean)
            .join(' ') || undefined
        }
        aria-invalid={props.error ? true : undefined}
      />
    </FieldShell>
  );
}

function TextField(props: FieldProps) {
  return (
    <FieldShell {...props}>
      <input
        id={props.id}
        type="text"
        className="input"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        aria-describedby={props.hint ? `${props.id}-hint` : undefined}
      />
    </FieldShell>
  );
}

function SelectField(props: FieldProps & { options: { value: string; label: string }[] }) {
  return (
    <FieldShell {...props}>
      <select
        id={props.id}
        className="input"
        value={props.value}
        onChange={(e) => props.onChange(e.target.value)}
        aria-invalid={props.error ? true : undefined}
        aria-describedby={props.error ? `${props.id}-error` : undefined}
      >
        {props.options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}
