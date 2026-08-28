# KAVACH — Agronomic Parameter Source Audit (Phase 1.5B)

Research-only audit of the 23 parameters currently `missing` / `source_needed` in
`backend/app/services/seed_agronomics.py` (`_MISSING_PARAMETERS`). **No database
changes, schema changes, or code changes were made.** This document is the
deliverable.

Method: WebSearch + WebFetch against FAO, ICAR-adjacent/Indian agricultural
university, USDA/NRCS, peer-reviewed journal, and university-extension sources
only. Commercial/blog/SEO sources are named explicitly where encountered and
are **not** used as the basis for any classification.

Statuses used: **SOURCE-DERIVED**, **DERIVED** (computed, not stored),
**MODEL-ASSUMPTION**, **CONTEXT-DEPENDENT**, **NOT-REQUIRED**, **SOURCE-NEEDED**.

---

## Master table

| # | Parameter | Status | Recommended value/range | Source | Context | MVP relevance | Notes |
|---|---|---|---|---|---|---|---|
| 1 | `kc_initial` | SOURCE-DERIVED | 0.53 (polyhouse, insect-net NVP) / 0.51 (shade net) / 0.51 (open field) | Sharma & Changade (2025), *J. Agrometeorol.* 27(2):157–162 | Protected cultivation, drip-irrigated tomato, Jalandhar, Punjab, autumn season (Aug–Nov) | Can wait (needed only if ETc-method water calc is chosen) | Stage = 1–26 days after sowing (DAS). The 0.53 figure is the *actual* number previously "discussed" — now verified. |
| 2 | `kc_mid` | SOURCE-DERIVED | 1.08 (polyhouse) / 1.05 (shade net) / 1.10 (open field) | Same as #1 | Same as #1 | Can wait | Stage = 63–99/100 DAS (peak Kc). |
| 3 | `kc_late` | SOURCE-DERIVED | 0.63 (polyhouse) / 0.61 (shade net) / 0.67 (open field) | Same as #1 | Same as #1 | Can wait | Stage = 100–120 DAS. |
| 4 | `eto_reference_mm_day` | DERIVED | Not a fixed value — computed via FAO Penman-Monteith from Rn, T, G, u₂, vapour-pressure deficit, ψ. Illustrative range observed in polyhouse context: 1.2–3.7 mm/day (stage-dependent) | FAO-56 (Allen et al., 1998) methodology; illustrative range from Sharma & Changade (2025) | Polyhouse, Punjab | Can wait | Should never be a stored constant. |
| 5 | `crop_water_requirement_mm_day` | DERIVED | ETc = Kc × ETo. Illustrative polyhouse range: 1.88–3.88 mm/day (stage-dependent) | Conceptually FAO-56; illustrative range from Sharma & Changade (2025) | Polyhouse, Punjab | Can wait | **Architecture flag**: this should not exist as a static `agronomic_parameters` row at all — it is an output of a calculation over Kc/ETo, not a fact to look up. |
| 6 | `irrigation_efficiency_pct` | SOURCE-NEEDED | — | Not found this session | Drip/polyhouse | Can wait | No FAO/USDA-specific drip-efficiency citation was retrieved in this research pass — do not assume a number. Also an architecture flag: this is arguably an **irrigation-system configuration value** (measured per installation), not a crop-agronomy fact — recommend it live in a future irrigation-system model, not `agronomic_parameters`. |
| 7 | `temperature_min_c` | SOURCE-DERIVED, CONTEXT-DEPENDENT | Stage-dependent lower critical thresholds: germination <15°C; early vegetative <12°C; flowering/fruit-set <10°C; no growth below 12°C (species-level) | Deuter & Carey (DAF Qld, Drought and Climate Adaptation Program, 2023), *Tomato — Critical Temperature Thresholds*, citing Lovatt et al. (1998) and Heuvelink et al. (2020) | **Open-field, Australian varieties** — not protected-cultivation, not Indian | Not in current MVP scenario set (no cold/frost scenario planned) | No credible source ties a *single* min-temperature number to protected cultivation; value is stage-specific by definition. |
| 8 | `temperature_max_c` | SOURCE-DERIVED, CONTEXT-DEPENDENT | Stage-dependent upper critical thresholds: vegetative growth minimal >35°C; flowering/fruit-set >27°C (operational team threshold: 29°C for 3 consecutive days); fruit growth >32°C. Greenhouse literature: fruit-set failure ≥32°C (Adams et al., 2001); >30°C failure in one source (Kittas et al., 2005) | Deuter & Carey (2023) DAF Qld; Shamshiri et al. (2018), *Int. Agrophys.* 32:287–302 (Table 1, compiling Adams et al. 2001, Kittas et al. 2005, and others) | Open-field (Qld source) and greenhouse (Shamshiri review) — both non-Indian | **Required for MVP** (defines the heatwave scenario and feeds the already-scaffolded `heat_stress` stress condition) | Internal inconsistency found in the DAF Qld source itself: body text says germination is reduced ">35°C" but its own summary table lists germination's upper critical as ">25". Reported here, not silently resolved. |
| 9 | `temperature_critical_stress_c` | SOURCE-DERIVED | Pollen germination/tube development reduced >30°C (Vasil, 1987); severe cellular damage at 45°C, short exposure (Qu et al., 2009); heat-tolerant cultivars affected once temperatures exceed 32°C, sensitive cultivars above 25°C (Sato et al., 2006) | Compiled in "An overview of heat stress in tomato" review, PMC7938145 | General / not protected-cultivation-specific | **Required for MVP** (heat-stress detection) | **Could not verify the specific "22/26°C optimum, ≥35°C day/≥26°C night screening" figures previously attributed to an ICAR study.** The closest verified Indian/ICAR-adjacent literature found describes a 32°C day/26°C night (or ≥32°C day / >20°C night) screening regime for pollen-viability trials at ICAR-IIVR, Varanasi (2013–2016) — a different pair of numbers. Do not use the 22/26 / 35/26 figures until a specific citation is located. |
| 10 | `humidity_min_pct` | SOURCE-DERIVED, CONTEXT-DEPENDENT | Stage/light-dependent; failure floor as low as 30–40% (vegetative, night); optimal generally 50–70% across the crop cycle; pollination best around 60–70% | Shamshiri et al. (2018) *Int. Agrophys.* 32:287–302, Table 4 (HYTODMOD model); Huang et al. (2011); Harel et al. (2014) | Greenhouse tomato, general (Malaysia/Ohio/Israel studies, not India-specific) | Can wait | ASABE (2015) standard cites 60–90% as broadly appropriate. |
| 11 | `humidity_max_pct` | SOURCE-DERIVED, CONTEXT-DEPENDENT | Stage/light-dependent; optimal upper bound 80–100% depending on stage; >90% increases pollen heat-susceptibility; disease risk rises sharply above ~85–90% | Shamshiri et al. (2018), same as #10; Nepi et al. (2010) | Greenhouse tomato, general | Can wait | The review's authors argue **VPD (vapour pressure deficit)**, not RH alone, is the scientifically better-founded control variable (optimal VPD ≈ 0.3–1.0 kPa, multiple sources agree in that band). Worth considering as the actual parameter to adopt later instead of RH bounds. |
| 12 | `dli_target_mol_m2_day` | PARTIALLY SOURCE-DERIVED / SOURCE-NEEDED | Transplant/seedling stage: 15–20 mol·m⁻²·d⁻¹ (sourced). Mature production stage: 20–30(–35) mol·m⁻²·d⁻¹ appears repeatedly but **only in commercial LED-grow-light vendor blogs** | Wuetcher & Owen (2025), Purdue University *Vegetable Crops Hotline* (transplant figure only) | Greenhouse tomato transplants, US extension | Not in current MVP scope (no light-based decision planned) | The mature-stage range is explicitly excluded per this audit's sourcing rules (commercial/SEO content) — do not use it. Remember: ICAR's *observed* `dli_mol_m2_day` in `tomato_reference_profile` is not the same thing as a scientifically-established *target*. |
| 13 | `soil_field_capacity_pct` | CONTEXT-DEPENDENT | No single value — inherently soil-texture-specific. Definitional convention: water content at −10 kPa suction (sandy soils) to −33 kPa (loam/clay soils, USDA/NRCS convention). Illustrative texture-class spread found: sand ≈10–15% by volume, clay can exceed 30–40% | USDA/NRCS soil-water definitions (multiple NRCS/extension sources); exact USDA texture-class table could not be extracted this session (PDF fetch timeouts) | Soil-texture-dependent, not crop-specific | **Required for MVP** (bounds the simulator's plausible soil-moisture range and the validator's "excessive moisture" check) | **Architecture recommendation**: KAVACH needs a configured **soil profile** (texture class → FC/PWP), not one fixed KB number. |
| 14 | `soil_permanent_wilting_point_pct` | CONTEXT-DEPENDENT | No single value — texture-specific. Definitional convention: water content at −1500 kPa suction | Same NRCS/USDA convention as #13 | Soil-texture-dependent | **Required for MVP** (bounds the "water stress" floor) | Same architecture recommendation as #13 — pair FC+PWP with a soil-profile config, not fixed constants. |
| 15 | `soil_bulk_density_g_cm3` | SOURCE-NEEDED | — | Not found to a specific, citable source this session | Soil-texture-dependent | Can wait (only needed for volumetric/litres water-balance conversion, not the simpler %-deficit heuristic) | General ranges (~1.1–1.6 g/cm³ by texture) are common knowledge but were not verified against a specific credible source in this pass — do not store a number on that basis. |
| 16 | `root_zone_depth_cm` | SOURCE-DERIVED, CONTEXT-DEPENDENT | 70–150 cm (0.7–1.5 m); soil-water depletion fraction for no stress, p = 0.40 | FAO-56 (Allen et al., 1998), Table 22 | **Open-field, standard climate** — FAO-56's own standard conditions | Can wait (rigorous water-balance path only) | Protected-cultivation systems (containers, grow bags, raised beds) commonly restrict effective root depth well below FAO-56's open-field figure — this number should not be assumed to transfer directly to KAVACH's actual (currently unconfigured) growing medium/bed depth. |
| 17 | `soil_available_water_capacity_mm` | DERIVED | AWC = (Field Capacity − Permanent Wilting Point) × root-zone depth (unit conversion via bulk density if working on a mass basis) | Standard soil-physics relationship (USDA/NRCS) | — | Can wait | **Architecture flag**: same as `crop_water_requirement_mm_day` — this is a computed quantity from #13/#14/#15/#16, not an independent fact to store. |
| 18 | `soil_texture` | CONTEXT-DEPENDENT | Not applicable as a fixed value — this is a *configuration* field (the classification of KAVACH's actual polyhouse soil/substrate), not a crop-knowledge fact | — | — | Not required now | **Architecture recommendation**: move to a future soil-profile configuration model rather than `agronomic_parameters`. No component currently consumes it as crop knowledge. |
| 19 | `soil_ph` | SOURCE-DERIVED | 6.0–6.8 optimal (multiple sources converge); tolerant down to ~5.5 | Rutgers NJAES FS678; UNH Extension; University of Georgia CAES; NC State Extension; Cornell (via search-aggregated extension consensus) | **US home/commercial garden extension guidance, open-field/general** — not India-specific, not protected-cultivation-specific | Not required for MVP (nutrient management explicitly deferred; water is the primary objective) | Now sourced, but out of scope until a nutrient/fertigation phase exists. |
| 20 | `soil_ec_ds_m` | SOURCE-DERIVED | ECe threshold = 2.5 dS/m (saturated soil-paste extract); yield decline slope ≈ 9.9% per dS/m above threshold; rated "Moderately Sensitive" | FAO Annex 1, *Crop salt tolerance data* (fao.org/4/y4263e), compiling Maas & Hoffman (1977)-lineage data (Bierhuizen & Ploegman 1967; Hayward & Long 1943; Lyon 1941; Shalhevet & Yaron 1973) | Saturated soil-extract methodology — **not** the same measurement basis as fertigation/nutrient-solution EC typically monitored in drip/polyhouse systems | Not required for MVP (nutrient/salinity management deferred) | Real, credible, classic FAO source — but flag the methodology mismatch if this is ever compared against a drip-system EC sensor reading. |
| 21 | `n_total_requirement_g_plant_season` | SOURCE-DERIVED, CONTEXT-DEPENDENT | 200 kg N/ha total season (fertigated hybrid tomato, drip irrigation), split 10/40/30/20% across transplanting-establishment / flower-initiation-to-flowering / flowering-to-fruit-set / alternate-day-from-picking stages | TNAU (Tamil Nadu Agricultural University) Precision Farming Development Centre, *Tomato – Fertigation* schedule | Indian, hybrid tomato, drip-fertigated — a reasonably good contextual match to KAVACH, though not confirmed polyhouse-specific | Can wait / future (nutrient optimization is explicitly deferred past MVP) | Conversion to g/plant/season requires KAVACH's actual plant population/spacing, which is not yet configured — this is a genuine unit-conversion gap, not an invented number. This is a *prescriptive fertigation dose*, not a duplicate of Phase 0's *descriptive* day-by-day `n_demand_g_plant_day` — the two could be cross-checked for consistency once plant population is known, but should not be silently reconciled. |
| 22 | `p2o5_total_requirement_g_plant_season` | SOURCE-DERIVED, CONTEXT-DEPENDENT | 250 kg P₂O₅/ha total season, same stage split as #21 | Same TNAU source as #21 | Same as #21 | Can wait / future | The TNAU document's table header just says "P", but the fertilizer grades used (19:19:19, 12:61:0, 13:0:45) are standard Indian water-soluble-fertilizer grades expressed as N:P₂O₅:K₂O — so "P" here is inferred to mean P₂O₅, consistent with the fertilizer-industry convention, not stated in so many words in the source text. Flagging this inference explicitly. Kept explicitly distinct from `soil_p_mg_kg` (elemental P) throughout. |
| 23 | `k2o_total_requirement_g_plant_season` | SOURCE-DERIVED, CONTEXT-DEPENDENT | 250 kg K₂O/ha total season, same stage split as #21 | Same TNAU source as #21 | Same as #21 | Can wait / future | Same inference caveat as #22 (grade convention → K₂O). Kept explicitly distinct from `soil_k_mg_kg` (elemental K) throughout. |

---

## SECTION 1 — Source-backed values

Full citation detail for every parameter landing on real, checkable sources.

### Kc (initial / mid / late) — protected cultivation, Punjab
- **Value**: initial 0.53, mid 1.08, late 0.63 (naturally-ventilated polyhouse with insect-net side ventilation)
- **Alternate structures, same paper**: shade net house 0.51 / 1.05 / 0.61; open field 0.51 / 1.10 / 0.67
- **Crop / stage**: tomato; initial = 1–26 DAS, development = 27–62 DAS, mid = 63–99/100 DAS, late = 100–120 DAS, end = >120 DAS
- **Cultivation context**: drip-irrigated tomato under LDPE (200 µm) naturally-ventilated polyhouse with insect-net side vents; autumn seasons Aug 1 – Nov 30, 2023 and 2024; planting density 50×30 cm
- **Source**: Sharma, V. & Changade, N.M. (2025). "Empirically derived crop coefficient values for tomatoes grown in protected structure under climatic condition of Jalandhar, Punjab." *Journal of Agrometeorology*, 27(2), 157–162. https://doi.org/10.54386/jam.v27i2.2953
- **Method**: FAO Penman-Monteith for ETo; soil-water-balance method for ETc; Kc = ETc/ETo
- **Limitations**: single location (Jalandhar, Punjab, 31.25°N), two autumn seasons only — not validated for other Indian regions, other seasons, or other polyhouse construction types.

### Root-zone depth and depletion fraction (FAO-56)
- **Value**: Zr = 0.7–1.5 m; p (no-stress depletion fraction) = 0.40, at ETc ≈ 5 mm/day
- **Crop**: tomato, standard/open-field conditions
- **Source**: Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998). *Crop Evapotranspiration — Guidelines for Computing Crop Water Requirements*. FAO Irrigation and Drainage Paper No. 56, Table 22. https://www.fao.org/4/x0490e/x0490e0e.htm
- **Limitation**: FAO-56's own standard/open-field assumption — protected-cultivation containerized/raised-bed systems commonly have shallower effective root zones.

### FAO-56 single Kc values (open field, for context/comparison only — NOT used as KAVACH's Kc)
- **Value**: Kc ini = 0.6, Kc mid = 1.15 (or 1.20 for tall/staked tomato >1.5–2 m), Kc end = 0.70–0.90
- **Source**: FAO-56, Table 12. https://www.fao.org/4/x0490e/x0490e0b.htm
- **Context**: subhumid climate reference conditions (RHmin ≈ 45%, u₂ ≈ 2 m/s), open field
- **Why not used**: open field, not protected cultivation — the Sharma & Changade (2025) polyhouse-specific values are the better match for KAVACH.

### Temperature thresholds — DAF Queensland
- **Source**: Deuter, P. & Carey, D. (2023). *Tomato — Critical Temperature Thresholds*. Drought and Climate Adaptation Program (DCAP), Dept. of Agriculture and Fisheries, Queensland. https://data.longpaddock.qld.gov.au/static/dcap/DCAP3/DCAP%203__12%20Tomato%20CTT%20Final.pdf
- **Scope stated by the source itself**: "This report applies to the fresh **outdoor** tomato industry only" — explicitly excludes greenhouse/glasshouse production.
- **Table 1 (optimum/critical by stage)**:
  | Stage | Optimum range (°C) | Critical thresholds (°C) |
  |---|---|---|
  | Seed germination | 20–30 | <15, >25 (table) / >35 (body text — inconsistent within the source) |
  | Early vegetative growth | 26–30 | <12, >35 |
  | Flowering, pollination, fruit set | 18–24 | <10, >27 (29°C for 3 consecutive days used operationally) |
  | Fruit growth | 23–26 | <0 (as printed), >32 |

### Temperature/RH/VPD review — greenhouse tomato (Int. Agrophys.)
- **Source**: Shamshiri, R.R., Jones, J.W., Thorp, K.R., Ahmad, D., Che Man, H., Taheri, S. (2018). "Review of optimum temperature, humidity, and vapour pressure deficit for microclimate evaluation and control in greenhouse cultivation of tomato: a review." *International Agrophysics*, 32, 287–302. https://doi.org/10.1515/intag-2017-0005
- Extensive Table 1 (>30 literature-sourced T thresholds by stage), Table 4 (stage/light-specific optimal & failure T/RH/VPD for cultivar 'Caruso'), Tables 2–3 (VPD 0.3–1.0 kPa optimal, multiple sources).
- Direct relevance: this is greenhouse-specific (not open-field), matching KAVACH's polyhouse context far better than the DAF Qld document.

### DLI — tomato transplants
- **Value**: 15–20 mol·m⁻²·d⁻¹
- **Source**: Wuetcher, L.T. & Owen, W.G. (2025, March 11). "Managing Daily Light Integral to Improve Vegetable Transplant Quality." *Purdue University Vegetable Crops Hotline*. https://vegcropshotline.org/article/managing-daily-light-integral-to-improve-vegetable-transplant-quality/
- **Limitation**: transplant/seedling stage only — does not cover the mature-crop portion of the Day 1–120 ICAR span.

### Soil pH
- **Value**: 6.0–6.8 optimal, tolerant to ~5.5
- **Sources**: Rutgers NJAES FS678 (njaes.rutgers.edu/fs678); University of New Hampshire Extension; University of Georgia CAES Field Report; NC State Extension
- **Limitation**: US home/commercial garden extension guidance — general, not India- or protected-cultivation-specific.

### Soil salinity (EC)
- **Value**: ECe threshold 2.5 dS/m (saturated soil-paste extract), yield decline ≈9.9%/dS/m above threshold, "Moderately Sensitive" rating
- **Source**: FAO. *Annex 1 — Crop salt tolerance data*. https://www.fao.org/4/y4263e/y4263e0e.htm (compiling Maas & Hoffman, 1977-lineage studies)
- **Limitation**: saturated soil-extract methodology differs from fertigation-solution/drainage EC monitoring typical of drip/polyhouse systems.

### N/P₂O₅/K₂O season fertigation dose
- **Value**: 200:250:250 kg NPK/ha for hybrid tomato, split 10/40/30/20% across four crop stages
- **Source**: Tamil Nadu Agricultural University (TNAU), Precision Farming Development Centre. *Tomato – Fertigation* schedule. https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf
- **Context**: Indian, hybrid tomato, drip-fertigated.
- **Limitation**: a prescriptive practice recommendation, not confirmed polyhouse-specific; "P"/"K" column labels are interpreted as P₂O₅/K₂O by fertilizer-grade convention, not stated explicitly as such in the source text.

---

## SECTION 2 — Derived parameters (must not be stored as fixed values)

- **`eto_reference_mm_day`** — computed from the FAO Penman-Monteith equation given real-time weather inputs (net radiation, air temperature, soil heat flux, wind speed, vapour pressure deficit, psychrometric constant). Not a lookup constant.
- **`crop_water_requirement_mm_day`** — ETc = Kc × ETo (or a water-balance equivalent). Depends on two other quantities that are themselves context/measurement-dependent.
- **`soil_available_water_capacity_mm`** — AWC = (Field Capacity − Permanent Wilting Point) × root-zone depth. A function of three other soil-profile inputs.

None of these three should exist as static rows in `agronomic_parameters` once their inputs are available — they belong in a future calculation service, not the knowledge base.

## SECTION 3 — Context-dependent parameters

- **`soil_field_capacity_pct`**, **`soil_permanent_wilting_point_pct`** — inherently soil-texture-specific; KAVACH needs a configured soil profile (texture class or measured values), not one number.
- **`root_zone_depth_cm`** — FAO-56's 0.7–1.5 m is an open-field standard; protected-cultivation growing-medium depth (containers, grow bags, raised beds) needs its own configuration once KAVACH's physical setup is known.
- **`humidity_min_pct` / `humidity_max_pct`** — genuinely stage- and light-condition-dependent per the reviewed literature (not a single band).
- **`temperature_min_c` / `temperature_max_c`** — genuinely stage-dependent (germination vs. vegetative vs. flowering vs. fruit growth all have different thresholds).
- **`n_total_requirement_g_plant_season`, `p2o5_total_requirement_g_plant_season`, `k2o_total_requirement_g_plant_season`** — sourced at the per-hectare level; converting to per-plant requires KAVACH's actual plant population/spacing, which is not yet configured.

## SECTION 4 — Parameters that should not be stored as fixed values

- **`crop_water_requirement_mm_day`**, **`soil_available_water_capacity_mm`** — computed outputs (see Section 2). Recommend removing these two rows from `agronomic_parameters` once a calculation service exists, rather than seeding placeholder facts for them.
- **`soil_texture`** — recommend moving to a future **soil-profile configuration model** (alongside FC/PWP/bulk density once sourced), not `agronomic_parameters`. No current component consumes it as "crop knowledge."
- **`irrigation_efficiency_pct`** — recommend moving to a future **irrigation-system configuration model** (it describes a specific physical installation, not the crop).

## SECTION 5 — Parameters still genuinely lacking a credible source

- **`irrigation_efficiency_pct`** — no FAO/USDA-specific citation retrieved this session.
- **`soil_bulk_density_g_cm3`** — no specific credible citation retrieved this session (common "~1.1–1.6 g/cm³" figures exist in general knowledge but were not verified to a citable source here).
- **`dli_target_mol_m2_day` (mature-crop stage)** — only commercial/LED-vendor blog sources found (indoorfarmsys.com, thriveagritech.com, hortamericas.com, growwithhydroponics.com); explicitly excluded per this audit's sourcing rules. The transplant-stage figure (15–20 mol·m⁻²·d⁻¹, Purdue) IS sourced — see Section 1.
- **`temperature_critical_stress_c`** (the specific "22/26°C optimum, ≥35°C/≥26°C screening" figures previously attributed to an ICAR study) — **could not verify**. Related but numerically different Indian/ICAR-adjacent literature (32°C day/26°C night pollen-viability screening at ICAR-IIVR, Varanasi, 2013–2016) was found instead. Treat the originally-quoted 22/26 and 35/26 figures as unconfirmed until a specific citation is located.
- **`soil_field_capacity_pct` / `soil_permanent_wilting_point_pct`** — the general USDA/NRCS definitions and methodology are solidly sourced, but the specific USDA texture-class value table could not be extracted this session (repeated PDF-fetch timeouts against nrcs.usda.gov and extension.okstate.edu). The *architecture conclusion* (texture-specific, needs a soil profile, not one number) does not depend on recovering that exact table, but the precise per-texture numbers remain open for a future session.

## SECTION 6 — Recommended final MVP parameter set

Given the water-optimization MVP objective and the roadmap's stated scenario set (normal, heatwave, water shortage, excess irrigation), the parameters that actually gate MVP work are:

- `temperature_max_c` and `temperature_critical_stress_c` — define the heatwave scenario and the `heat_stress` condition.
- `soil_field_capacity_pct` and `soil_permanent_wilting_point_pct` — define the physically plausible soil-moisture band for both the simulator and the validator.

Everything else in this audit is either (a) genuinely deferrable to a later phase, (b) architecturally a computed value or a configuration field rather than a knowledge-base fact, or (c) tied to nutrient/fertigation/light features the project has explicitly deferred past the water-focused MVP.

---

## FINAL RECOMMENDATION

**What exact agricultural parameters should KAVACH actually depend on before Phase 2?**

**ESSENTIAL NOW**
- `temperature_max_c`
- `temperature_critical_stress_c`
- `soil_field_capacity_pct`
- `soil_permanent_wilting_point_pct`

(All four are now source-backed in principle — see Section 1 — but the exact numbers to load still need a deliberate sourcing decision, since the available sources are open-field/non-Indian/general-greenhouse rather than a perfect polyhouse+India match. Recommend explicitly choosing which cited value to adopt, with the mismatch documented, rather than treating any one as a silent default.)

**CAN WAIT**
- `kc_initial`, `kc_mid`, `kc_late` (sourced — Sharma & Changade 2025 — but only needed once an ETc-based water-requirement method is chosen over a simpler moisture-deficit heuristic)
- `eto_reference_mm_day`, (as a documented derivation, not a stored value)
- `humidity_min_pct`, `humidity_max_pct`
- `root_zone_depth_cm`, `soil_bulk_density_g_cm3`
- `n_total_requirement_g_plant_season`, `p2o5_total_requirement_g_plant_season`, `k2o_total_requirement_g_plant_season`

**FUTURE**
- `dli_target_mol_m2_day` (mature stage)
- `temperature_min_c` (no cold-stress scenario currently planned)
- `soil_ph`, `soil_ec_ds_m` (nutrient/salinity management, explicitly deferred)

**SHOULD BE DERIVED (never stored as a fixed KB row)**
- `crop_water_requirement_mm_day`
- `soil_available_water_capacity_mm`

**SHOULD BE MOVED TO CONFIGURATION**
- `soil_texture` → future soil-profile config model
- `irrigation_efficiency_pct` → future irrigation-system config model

**NOT NEEDED (given the current MVP's water-only objective)**
- `soil_ph`, `soil_ec_ds_m`, and the three N/P₂O₅/K₂O season-total parameters are all real, sourced facts, but none are consumed by anything in the water-optimization MVP scope. They can stay `source_needed`→ now `sourced` in the KB for completeness/traceability without being wired into any Phase 2 logic.

---

*No database rows were populated by this audit. All figures above are reported for review; loading any of them into `agronomic_parameters` requires an explicit follow-up decision, especially given that several (Kc, temperature thresholds, DLI, N/P/K) are ranges or stage-dependent series rather than single numbers, and the current schema's `value_numeric` is a single float — extending it to store a range (e.g. `value_min` / `value_max`) is a schema change worth considering before populating anything from Section 1.*
