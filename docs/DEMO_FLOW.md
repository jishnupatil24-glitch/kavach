# KAVACH — Demonstration Flow

The intended end-to-end walkthrough, using only fields actually present in the implemented API responses (see `docs/API_CONTRACT.md`). Every field name below is real.

```
1. Select farm/run
       GET /api/simulator/runs  ->  pick a run_id
       (or POST /api/simulator/runs to generate a new one)
            |
            v
2. View current farm state
       GET /api/analysis/tomato/runs/{run_id}?day=D
       -> per-variable current value, trend direction, rate, ICAR deviation, crop stage
            |
            v
3. View detected problems
       GET /api/assessment/tomato/runs/{run_id}?day=D
       -> 10 categories, each with status/severity/abnormal_state_duration
       -> filter to status in (weak_evidence, corroborated_evidence) for a "problems that matter" view;
          insufficient_data/no_evidence categories are real API entries, not errors -- just not actionable
            |
            v
4. View recommendations
       GET /api/decision/tomato/runs/{run_id}?day=D
       -> filter to outcome == "ACTION_RECOMMENDED"
       -> show action_label, severity, eligibility_checks (with any `passed: null` shown as "not evaluable", not hidden)
            |
            v
5. Select a recommended action
       (frontend-side selection among the ACTION_RECOMMENDED entries from step 4)
            |
            v
6. View optimized intervention
       GET /api/optimization/tomato/runs/{run_id}?day=D
       -> find the matching entry in water_optimizations[] or nutrient_optimizations[] by `category`
       -> if the category instead appears in `unsupported[]`, show Phase 5's qualitative
          recommendation as-is, with the `reason` string explaining why no quantity exists
            |
            v
7. View quantity per plant
       water_optimizations[].baseline_l_per_plant_day / optimized_l_per_plant_day
       nutrient_optimizations[].baseline_g_per_plant_day / optimized_g_per_plant_day
       -> if null, show "UNAVAILABLE" with the matching entry in `limitations[]`, not a blank/zero
            |
            v
8. View total field quantity
       water_optimizations[].baseline_l_per_day / optimized_l_per_day
       nutrient_optimizations[].total_kg_per_day / baseline_total_kg_per_day
       -> null whenever plant_population.source == "UNKNOWN" -- show the population source/note,
          prompt farm configuration if population is missing
            |
            v
9. View duration
       review_cycle_days (both water and nutrient objects) -- an operational re-evaluation
       cadence, NOT a claim about crop physiology recovery time; label it that way in the UI
            |
            v
10. View resource savings / feasibility / cost
       water_saved_l_per_day, water_saving_percentage, total_water_saved_liters
       feasibility[] (available_water, pump_capacity) -- PASS/FAIL/NOT_EVALUATED
       cost.status -- AVAILABLE/UNAVAILABLE, cost_change (signed: negative = saving, positive = more expensive)
            |
            v
11. View provenance and assumptions
       every *_provenance / *_basis field: SOURCED / PROJECT_DEFINED / MODELED
       top-level `limitations[]` -- always show the "Prototype optimization model" disclaimer
```

## Notes specific to this flow

- **Farm configuration** is a prerequisite for steps 8-10 to show real numbers, not an optional side quest — without it, `plant_population.source == "UNKNOWN"` and every field-total/feasibility/cost value is `null`. Prompt for it early (`POST /api/optimization/tomato/runs/{run_id}/farm-config`).
- **Not every run/day reaches step 6 with a number.** A real, verified example (run 584, day 37) shows `baseline_l_per_plant_day: null` because that day falls in a crop-growth-stage window (`kc_development_stage`, day 27-62) with no approved baseline parameter. This is the backend working correctly (refusing to guess), not a bug — show it as "Baseline unavailable for this stage" rather than treating it as an error state. See `docs/DEMO_DATA.md` for a run/day that *does* produce full numbers.
- **Multiple simultaneous actions**: a day can have more than one `ACTION_RECOMMENDED` category (e.g. `excessive_moisture` + `heat_related` together, seen on real run 584). Design the UI to show a list of recommendations/optimizations, not a single-card assumption.
