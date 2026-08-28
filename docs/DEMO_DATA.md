# KAVACH — Demo Data (Verified Real Runs)

Every number below was read directly from the live `backend/kavach.db` / the running API this session, not fabricated. Use these run IDs for frontend development instead of generating new ones.

---

## Run 582 — `water_shortage`, severe (RECOMMENDED: full numeric demo)

- **Scenario:** `water_shortage`, severity `severe`, 30-day run, scenario window day 2-26.
- **Farm configuration:** set (labelled `"DEMO configuration (Phase 6 real-run demonstration, not a real farmer input)"`), `field_area=1 acre`, `plant_population=8000`, `irrigation_system_type=drip`, `water_cost_per_liter=0.0005`, `available_water_l_per_day=50000`, `pump_capacity_l_per_hour=3000`.
- **Best day for a full demo: day 7** (falls in `kc_initial_stage`, day 1-26 — a covered baseline window).

**Phase 5 result (day 7):** `water_depletion` → `ACTION_RECOMMENDED`, `status=weak_evidence`, `severity=HIGH`, `action_label="Increase irrigation"`.

**Phase 6 result (day 7) — verified, not estimated:**
```
baseline: 1.50 L/plant/day (kc_initial_stage, PROJECT_DEFINED)
adjustment: 30% increase (HIGH severity, PROJECT_DEFINED)
optimized: 1.95 L/plant/day (MODELED)
baseline field volume: 12,000 L/day
optimized field volume: 15,600 L/day
additional water required: 3,600 L/day (+30.0%)
total over 3-day review cycle: 10,800 L
irrigation efficiency: 85% (drip, system_type_lookup)
delivered baseline: 14,118 L/day   delivered optimized: 18,353 L/day
feasibility: available_water PASS, pump_capacity PASS
cost: baseline 7.06, optimized 9.18, change +2.12
expected direction: RISING (MODELED EXPECTED DIRECTION)
```
This is a **water-use increase** (water_depletion → more irrigation needed), not a saving — the sign is correct and intentional; see `docs/api-examples/optimization-run-example.json` for the full captured JSON.

---

## Run 584 — `excess_irrigation`, severe (shows the honest `UNAVAILABLE` case)

- **Scenario:** `excess_irrigation`, severity `severe`, 48-day run, scenario window day 31-46.
- **Farm configuration:** same DEMO label as run 582, same values.
- **Day 37:** `excessive_moisture` **and** `heat_related` **and** `humidity_low` are all `ACTION_RECOMMENDED` simultaneously (real multi-action example — humidity_low's presence here reflects Phase 4's pre-fix stale computation for this specific historical run, see `KAVACH_PROJECT_CONTEXT.md` section M; it is still a legitimate example of the multi-action UI case).
- **Phase 6 result (day 37):** `excessive_moisture`'s baseline is **`null` (`UNAVAILABLE`)** — day 37 falls in `kc_development_stage` (day 27-62), which has no approved baseline_irrigation parameter. `heat_related` and `humidity_low` appear in `unsupported[]` (qualitative-only, no resource model). This is the correct, intended behavior — use this run/day to build and test the "unavailable/qualitative-only" UI states, not just the happy path.

---

## Run 804 — `excess_irrigation`, severe, 95-day run, window shifted to land in `kc_mid_stage`

Created during Phase 6 implementation testing specifically to demonstrate the full non-`UNAVAILABLE` numeric chain (same scenario/severity/seed as the canonical test scenario, `scenario_start_day` shifted to 70 so the window falls in day 63-100 instead of 27-62).

- **Farm configuration:** `field_area=1 acre`, `plant_population=8000`, `irrigation_system_type=drip` (no cost/feasibility fields set on this one — use it for the "cost/feasibility not configured" states, or run 582/584 above for the fully-configured case).
- **Day 77** (`excessive_moisture`, MODERATE severity, `kc_mid_stage`):
```
baseline: 3.50 L/plant/day    optimized: 2.80 L/plant/day
baseline field volume: 28,000 L/day    optimized: 22,400 L/day
saved: 5,600 L/day (20.0%)    total over 3-day cycle: 16,800 L
feasibility: NOT_EVALUATED (no available_water/pump_capacity configured on this run)
cost: UNAVAILABLE (no water_cost_per_liter configured on this run)
```

---

## Runs NOT yet suitable for a clean numeric demo

The project's own two canonical named test scenarios (`excess_irrigation` day 34/38, `water_shortage` day 35/40 — see `backend/tests/test_decision_engine.py`) both land inside `kc_development_stage` (day 27-62), which has no approved irrigation baseline. If you regenerate those exact configs, expect `baseline_l_per_plant_day: null` — this is correct, not a bug. Use run 582 (above) or shift the scenario window later (like run 804) for a full-numbers walkthrough instead.

## Phase 6 verification status for all runs above

**"Phase 6 output for this run requires final verification"** applies to every number above in the sense that this project's separate final testing/verification workflow for Phase 6 has not yet run (see `docs/BACKEND_STATUS.md`). The numbers themselves were read directly from a live, passing backend during implementation — they are not fabricated — but treat them as implementation-verified, not product-verified, until that workflow completes.
