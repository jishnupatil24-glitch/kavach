"""
Seeds the agronomic knowledge base: sources, crop stages, agronomic
parameters, and stress-condition definitions.

Phase 1.5C: populates every parameter that the Phase 1.5B web-research
audit (docs/agronomic_parameter_audit.md) actually verified against a
credible source (FAO / ICAR-adjacent / USDA-NRCS / peer-reviewed /
university extension), with full provenance. Every other parameter is
left explicitly unresolved (status="source_needed") or marked as a
computed quantity (status="derived") / a site-specific configuration
fact (status="context_dependent") -- never fabricated.

A value is stored as exactly one of:
  - a single point (value_numeric), when the source gives one number.
  - a range (value_min/value_max), when the source gives a range or the
    parameter is genuinely a band -- never collapsed to a midpoint.
  - neither, when status is source_needed/derived/context_dependent.

Run:
    python -m app.services.seed_agronomics
"""
from __future__ import annotations

from dataclasses import dataclass

from app.database.session import Base, SessionLocal, engine
from app.models.agronomic_parameter import AgronomicParameter
from app.models.agronomic_source import AgronomicSource
from app.models.crop_stage import CropStage
from app.models.stress_condition import StressCondition

TOMATO = "tomato"


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

_ICAR_SOURCE = dict(
    key="icar",
    organization_or_author=None,
    title="ICAR-derived tomato polyhouse dataset",
    publication_year=None,
    source_type="PDF",
    document_reference="data/sources/icar/tomato_reference.pdf",
    description=(
        "Day 1-120 tomato polyhouse dataset: environmental conditions, "
        "target soil NPK concentration, and modelled daily nutrient "
        "demand. Same source document as Phase 0's `data_source` record; "
        "catalogued here with the richer agronomic-source schema."
    ),
    notes=(
        "Author, publisher, and publication date are not stated in the "
        "document itself and are left unknown rather than invented."
    ),
)

_SHARMA_CHANGADE_SOURCE = dict(
    key="sharma_changade_2025",
    organization_or_author="Sharma, V. & Changade, N.M.",
    title=(
        "Empirically derived crop coefficient values for tomatoes grown "
        "in protected structure under climatic condition of Jalandhar, "
        "Punjab"
    ),
    publication_year=2025,
    source_type="peer-reviewed journal article",
    document_reference="Journal of Agrometeorology, 27(2), 157-162, https://doi.org/10.54386/jam.v27i2.2953",
    description=(
        "Empirical Kc (crop coefficient) determination for drip-irrigated "
        "tomato in three cultivation systems -- naturally-ventilated "
        "polyhouse (insect-net side vents), shade-net house, and open "
        "field -- Jalandhar, Punjab, India, autumn seasons 2023 and 2024."
    ),
    notes=(
        "Single location (31.25 deg N), two autumn seasons only -- not "
        "validated for other Indian regions, other seasons, or other "
        "polyhouse construction types."
    ),
)

_FAO56_SOURCE = dict(
    key="fao56",
    organization_or_author="Allen, R.G., Pereira, L.S., Raes, D., Smith, M.",
    title="Crop Evapotranspiration - Guidelines for Computing Crop Water Requirements",
    publication_year=1998,
    source_type="FAO technical guideline",
    document_reference="FAO Irrigation and Drainage Paper No. 56, Table 22 / Table 12, https://www.fao.org/4/x0490e/x0490e00.htm",
    description=(
        "Standard FAO Penman-Monteith methodology for reference "
        "evapotranspiration (ETo) and crop coefficients (Kc), including "
        "standard/open-field tomato root-zone-depth and depletion-fraction "
        "guidance."
    ),
    notes="Standard/open-field reference conditions, not protected-cultivation-specific.",
)

_DAF_QLD_SOURCE = dict(
    key="daf_qld_2023",
    organization_or_author="Deuter, P. & Carey, D.",
    title="Tomato - Critical Temperature Thresholds",
    publication_year=2023,
    source_type="government technical report",
    document_reference=(
        "Drought and Climate Adaptation Program (DCAP), Queensland Dept. "
        "of Agriculture and Fisheries, "
        "https://data.longpaddock.qld.gov.au/static/dcap/DCAP3/DCAP%203__12%20Tomato%20CTT%20Final.pdf"
    ),
    description=(
        "Stage-specific optimum and critical temperature thresholds for "
        "tomato, compiling Lovatt et al. (1998) and Heuvelink et al. (2020)."
    ),
    notes=(
        "States explicitly it applies to the 'fresh outdoor tomato "
        "industry only' -- open field, Queensland, Australia; not "
        "protected-cultivation-specific. Source's own Table 1 and body "
        "text disagree on the germination upper-critical figure "
        "(>25C in the table vs >35C in the body text) -- both are "
        "preserved here rather than silently resolved."
    ),
)

_SHAMSHIRI_SOURCE = dict(
    key="shamshiri_2018",
    organization_or_author=(
        "Shamshiri, R.R., Jones, J.W., Thorp, K.R., Ahmad, D., Che Man, H., Taheri, S."
    ),
    title=(
        "Review of optimum temperature, humidity, and vapour pressure "
        "deficit for microclimate evaluation and control in greenhouse "
        "cultivation of tomato: a review"
    ),
    publication_year=2018,
    source_type="peer-reviewed review article",
    document_reference="International Agrophysics, 32, 287-302, https://doi.org/10.1515/intag-2017-0005",
    description=(
        "Review compiling >30 literature-sourced temperature thresholds "
        "and stage/light-specific optimal & failure temperature/humidity/"
        "VPD values (incl. cultivar 'Caruso') for greenhouse tomato."
    ),
    notes="Greenhouse-general; not India-specific. Compiles multiple primary studies.",
)

_PURDUE_DLI_SOURCE = dict(
    key="purdue_dli_2025",
    organization_or_author="Wuetcher, L.T. & Owen, W.G.",
    title="Managing Daily Light Integral to Improve Vegetable Transplant Quality",
    publication_year=2025,
    source_type="university extension article",
    document_reference="Purdue University Vegetable Crops Hotline, https://vegcropshotline.org/article/managing-daily-light-integral-to-improve-vegetable-transplant-quality/",
    description="DLI guidance for vegetable (incl. tomato) transplant/seedling production.",
    notes="Transplant/seedling stage only -- does not cover the mature-crop portion of the Day 1-120 ICAR span.",
)

_RUTGERS_PH_SOURCE = dict(
    key="rutgers_fs678",
    organization_or_author="Rutgers New Jersey Agricultural Experiment Station",
    title="Soil pH guidance for vegetable crops (incl. tomato), FS678",
    publication_year=None,
    source_type="university extension fact sheet",
    document_reference="https://njaes.rutgers.edu/fs678/",
    description="General US extension soil-pH guidance for tomato, corroborated by UNH Extension, UGA CAES, and NC State Extension.",
    notes="US home/commercial garden extension guidance -- general, not India- or protected-cultivation-specific.",
)

_FAO_SALT_SOURCE = dict(
    key="fao_salt_tolerance",
    organization_or_author="FAO",
    title="Annex 1: Crop salt tolerance data",
    publication_year=None,
    source_type="FAO technical annex",
    document_reference="https://www.fao.org/4/y4263e/y4263e0e.htm",
    description=(
        "Crop salt-tolerance thresholds (Maas & Hoffman, 1977-lineage "
        "data), compiling Bierhuizen & Ploegman 1967, Hayward & Long "
        "1943, Lyon 1941, Shalhevet & Yaron 1973."
    ),
    notes="Saturated soil-paste-extract methodology -- differs from fertigation-solution/drainage EC monitoring typical of drip/polyhouse systems.",
)

_TNAU_SOURCE = dict(
    key="tnau_fertigation",
    organization_or_author="Tamil Nadu Agricultural University (TNAU), Precision Farming Development Centre",
    title="Tomato - Fertigation schedule",
    publication_year=None,
    source_type="university extension technical schedule",
    document_reference="https://agritech.tnau.ac.in/horticulture/ferti_schedule.pdf",
    description="Prescriptive N/P/K fertigation dose (kg/ha) for hybrid tomato, drip-fertigated, split across four crop stages.",
    notes=(
        "Indian, hybrid tomato, drip-fertigated -- a reasonably good "
        "contextual match to KAVACH, though not confirmed "
        "polyhouse-specific. Per-hectare values; converting to "
        "per-plant requires KAVACH's plant population/spacing, which is "
        "not yet configured. 'P'/'K' column labels are interpreted as "
        "P2O5/K2O by standard Indian fertilizer-grade convention "
        "(19:19:19, 12:61:0, 13:0:45), not stated explicitly as such in "
        "the source text -- this inference is flagged, not silent."
    ),
)

_NRCS_SOIL_WATER_SOURCE = dict(
    key="nrcs_soil_water_convention",
    organization_or_author="USDA Natural Resources Conservation Service (NRCS)",
    title="Soil-water characteristic definitions (field capacity, permanent wilting point)",
    publication_year=None,
    source_type="government technical convention",
    document_reference=None,
    description=(
        "Standard soil-physics convention: field capacity as water "
        "content at approx. -10 kPa (sandy soils) to -33 kPa "
        "(loam/clay soils) suction; permanent wilting point at "
        "approx. -1500 kPa suction. Both are inherently soil-texture "
        "dependent, not universal percentages."
    ),
    notes=(
        "The specific USDA/NRCS per-texture-class value table could not "
        "be retrieved in the Phase 1.5B research session (repeated PDF "
        "fetch timeouts against nrcs.usda.gov / extension.okstate.edu). "
        "This source record documents the definitional convention only; "
        "no document_reference URL is stored because none was actually "
        "and successfully retrieved."
    ),
)

_HEAT_STRESS_REVIEW_SOURCE = dict(
    key="heat_stress_review_pmc7938145",
    organization_or_author=None,
    title="An overview of heat stress in tomato (review)",
    publication_year=None,
    source_type="peer-reviewed review article",
    document_reference="PMC7938145",
    description=(
        "Review compiling tomato heat-stress physiology findings, "
        "including pollen germination/tube development thresholds "
        "(citing Vasil, 1987), severe cellular damage thresholds "
        "(citing Qu et al., 2009), and cultivar-dependent heat "
        "tolerance/sensitivity thresholds (citing Sato et al., 2006)."
    ),
    notes=(
        "General tomato physiology, not protected-cultivation-specific. "
        "Primary studies (Vasil 1987, Qu et al. 2009, Sato et al. 2006) "
        "are cited as reported by this compiling review, not "
        "independently re-verified against the original papers this "
        "session. The previously-referenced '22/26C optimum, "
        ">=35C day />=26C night screening' ICAR figures could NOT be "
        "verified against any source found this session -- the closest "
        "real ICAR-adjacent literature located (ICAR-IIVR Varanasi "
        "heat-tolerance screening, 2013-2016) uses a 32C day/26C night "
        "pollen-viability screening regime instead, which is a "
        "different, separately-unverified figure not stored here."
    ),
)

_ALL_SOURCES = [
    _ICAR_SOURCE,
    _SHARMA_CHANGADE_SOURCE,
    _FAO56_SOURCE,
    _DAF_QLD_SOURCE,
    _SHAMSHIRI_SOURCE,
    _PURDUE_DLI_SOURCE,
    _RUTGERS_PH_SOURCE,
    _FAO_SALT_SOURCE,
    _TNAU_SOURCE,
    _NRCS_SOIL_WATER_SOURCE,
    _HEAT_STRESS_REVIEW_SOURCE,
]


# ---------------------------------------------------------------------------
# Crop stages
# ---------------------------------------------------------------------------
# Two independent stage taxonomies, each tied to its own source. Never
# merged into one -- different studies, different stage definitions.

_STAGES = [
    dict(
        key="full_cycle",
        name="full_cycle",
        start_day=1,
        end_day=120,
        description=(
            "Full Day 1-120 period covered by the ICAR reference profile. "
            "Sub-stage boundaries are not sourced from this document."
        ),
        source_key="icar",
    ),
    # Sharma & Changade (2025) DAS-based Kc stages -- real day windows.
    dict(
        key="kc_initial_stage",
        name="kc_initial_stage",
        start_day=1,
        end_day=26,
        description="Kc initial stage (1-26 days after sowing), per Sharma & Changade (2025).",
        source_key="sharma_changade_2025",
    ),
    dict(
        key="kc_development_stage",
        name="kc_development_stage",
        start_day=27,
        end_day=62,
        description="Kc development stage (27-62 DAS), per Sharma & Changade (2025).",
        source_key="sharma_changade_2025",
    ),
    dict(
        key="kc_mid_stage",
        name="kc_mid_stage",
        start_day=63,
        end_day=100,
        description="Kc mid-season stage (63-99/100 DAS, peak Kc), per Sharma & Changade (2025).",
        source_key="sharma_changade_2025",
    ),
    dict(
        key="kc_late_stage",
        name="kc_late_stage",
        start_day=100,
        end_day=120,
        description="Kc late-season stage (100-120 DAS), per Sharma & Changade (2025).",
        source_key="sharma_changade_2025",
    ),
    # DAF Qld (2023) phenological stages -- no day-number mapping given by
    # the source, so boundaries are left NULL rather than invented.
    dict(
        key="germination",
        name="germination",
        start_day=None,
        end_day=None,
        description="Seed germination stage, per DAF Qld (2023). No day-number mapping given by the source.",
        source_key="daf_qld_2023",
    ),
    dict(
        key="early_vegetative_growth",
        name="early_vegetative_growth",
        start_day=None,
        end_day=None,
        description="Early vegetative growth stage, per DAF Qld (2023). No day-number mapping given by the source.",
        source_key="daf_qld_2023",
    ),
    dict(
        key="flowering_fruit_set",
        name="flowering_fruit_set",
        start_day=None,
        end_day=None,
        description="Flowering, pollination, and fruit-set stage, per DAF Qld (2023). No day-number mapping given by the source.",
        source_key="daf_qld_2023",
    ),
    dict(
        key="fruit_growth",
        name="fruit_growth",
        start_day=None,
        end_day=None,
        description="Fruit growth stage, per DAF Qld (2023). No day-number mapping given by the source.",
        source_key="daf_qld_2023",
    ),
]


# ---------------------------------------------------------------------------
# Agronomic parameters
# ---------------------------------------------------------------------------

@dataclass
class ParamRow:
    domain: str
    parameter_name: str
    status: str
    unit: str | None = None
    value_numeric: float | None = None
    value_min: float | None = None
    value_max: float | None = None
    value_text: str | None = None
    stage_key: str | None = None
    context: str | None = None
    source_key: str | None = None
    notes: str | None = None


_KC_CONTEXT_JALANDHAR = "protected cultivation — naturally ventilated polyhouse, insect-net side vents; Jalandhar, Punjab, India; autumn season"
_KC_CONTEXT_SHADE_NET = "shade-net house; Jalandhar, Punjab, India; autumn season"
_KC_CONTEXT_OPEN_FIELD = "open field; Jalandhar, Punjab, India; autumn season"
_KC_SOURCE_NOTE = (
    "Sharma & Changade (2025) also report values for the other two "
    "cultivation systems in the same study, stored as separate rows "
    "with the same parameter_name and stage."
)

_PARAMETERS: list[ParamRow] = [
    # --- Kc: three parameter names x three cultivation-system contexts ---
    ParamRow("water", "kc_initial", "sourced", value_numeric=0.53, stage_key="kc_initial_stage", context=_KC_CONTEXT_JALANDHAR, source_key="sharma_changade_2025", notes=_KC_SOURCE_NOTE),
    ParamRow("water", "kc_initial", "sourced", value_numeric=0.51, stage_key="kc_initial_stage", context=_KC_CONTEXT_SHADE_NET, source_key="sharma_changade_2025", notes=_KC_SOURCE_NOTE),
    ParamRow("water", "kc_initial", "sourced", value_numeric=0.51, stage_key="kc_initial_stage", context=_KC_CONTEXT_OPEN_FIELD, source_key="sharma_changade_2025", notes="Open-field variant from the same study -- NOT the value KAVACH should default to (protected cultivation is the polyhouse row above)."),
    ParamRow("water", "kc_mid", "sourced", value_numeric=1.08, stage_key="kc_mid_stage", context=_KC_CONTEXT_JALANDHAR, source_key="sharma_changade_2025", notes=_KC_SOURCE_NOTE),
    ParamRow("water", "kc_mid", "sourced", value_numeric=1.05, stage_key="kc_mid_stage", context=_KC_CONTEXT_SHADE_NET, source_key="sharma_changade_2025", notes=_KC_SOURCE_NOTE),
    ParamRow("water", "kc_mid", "sourced", value_numeric=1.10, stage_key="kc_mid_stage", context=_KC_CONTEXT_OPEN_FIELD, source_key="sharma_changade_2025", notes="Open-field variant from the same study -- NOT the value KAVACH should default to."),
    ParamRow("water", "kc_late", "sourced", value_numeric=0.63, stage_key="kc_late_stage", context=_KC_CONTEXT_JALANDHAR, source_key="sharma_changade_2025", notes=_KC_SOURCE_NOTE),
    ParamRow("water", "kc_late", "sourced", value_numeric=0.61, stage_key="kc_late_stage", context=_KC_CONTEXT_SHADE_NET, source_key="sharma_changade_2025", notes=_KC_SOURCE_NOTE),
    ParamRow("water", "kc_late", "sourced", value_numeric=0.67, stage_key="kc_late_stage", context=_KC_CONTEXT_OPEN_FIELD, source_key="sharma_changade_2025", notes="Open-field variant from the same study -- NOT the value KAVACH should default to."),

    # --- Derived: never a fixed fact ---
    ParamRow("water", "eto_reference_mm_day", "derived", unit="mm/day", notes=(
        "Computed via FAO Penman-Monteith from net radiation, air "
        "temperature, soil heat flux, wind speed, and vapour-pressure "
        "deficit -- not a lookup constant. Illustrative polyhouse range "
        "observed by Sharma & Changade (2025): 1.2-3.7 mm/day "
        "(stage-dependent), reported for context only, not stored as a "
        "value here."
    ), source_key="fao56"),
    ParamRow("water", "crop_water_requirement_mm_day", "derived", unit="mm/day", notes=(
        "ETc = Kc x ETo (or a water-balance equivalent). Depends on two "
        "quantities that are themselves context/measurement-dependent. "
        "Architecture note: this should not exist as a static "
        "agronomic_parameters row once a calculation service exists -- "
        "it is an output, not a fact to look up."
    ), source_key="fao56"),

    # --- Context-dependent (configuration), not crop knowledge ---
    ParamRow("water", "irrigation_efficiency_pct", "context_dependent", unit="%", notes=(
        "No FAO/USDA-specific drip-efficiency citation was retrieved. "
        "Also architecturally a farm/irrigation-system CONFIGURATION "
        "value (measured per installation), not a crop-agronomy fact -- "
        "recommend a future irrigation-system configuration model."
    )),

    # --- Temperature: DAF Qld stage-linked thresholds ---
    ParamRow("temperature", "temperature_min_c", "sourced", unit="°C", value_numeric=15.0, stage_key="germination", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Lower critical threshold ('<15C'); source scope is outdoor/open-field tomato only."),
    ParamRow("temperature", "temperature_min_c", "sourced", unit="°C", value_numeric=12.0, stage_key="early_vegetative_growth", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Lower critical threshold ('<12C')."),
    ParamRow("temperature", "temperature_min_c", "sourced", unit="°C", value_numeric=10.0, stage_key="flowering_fruit_set", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Lower critical threshold ('<10C')."),
    ParamRow("temperature", "temperature_min_c", "sourced", unit="°C", value_numeric=0.0, stage_key="fruit_growth", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Source prints '<0C' for this stage's lower critical threshold -- preserved as printed, flagged here as a plausible source oddity rather than silently corrected."),
    ParamRow("temperature", "temperature_max_c", "sourced", unit="°C", value_numeric=25.0, stage_key="germination", context="open field, Queensland, Australia — per DAF Qld Table 1 (summary table)", source_key="daf_qld_2023", notes="CONFLICTS with the source's own body text for this same stage (see the other germination row, 35C) -- both preserved, not silently resolved."),
    ParamRow("temperature", "temperature_max_c", "sourced", unit="°C", value_numeric=35.0, stage_key="germination", context="open field, Queensland, Australia — per DAF Qld body text", source_key="daf_qld_2023", notes="CONFLICTS with the source's own Table 1 for this same stage (see the other germination row, 25C) -- both preserved, not silently resolved."),
    ParamRow("temperature", "temperature_max_c", "sourced", unit="°C", value_numeric=35.0, stage_key="early_vegetative_growth", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Upper critical threshold ('>35C')."),
    ParamRow("temperature", "temperature_max_c", "sourced", unit="°C", value_numeric=27.0, stage_key="flowering_fruit_set", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Upper critical threshold ('>27C'); source also notes an operational screening threshold of 29C sustained for 3 consecutive days."),
    ParamRow("temperature", "temperature_max_c", "sourced", unit="°C", value_numeric=32.0, stage_key="fruit_growth", context="open field, Queensland, Australia", source_key="daf_qld_2023", notes="Upper critical threshold ('>32C')."),

    # --- Temperature: general heat-stress-review thresholds (not DAF-stage-linked) ---
    ParamRow("temperature", "temperature_critical_stress_c", "sourced", unit="°C", value_numeric=30.0, context="pollen germination / tube development", source_key="heat_stress_review_pmc7938145", notes="As cited from Vasil (1987) by the compiling review; not independently re-verified against the original paper."),
    ParamRow("temperature", "temperature_critical_stress_c", "sourced", unit="°C", value_numeric=45.0, context="severe cellular damage, short exposure", source_key="heat_stress_review_pmc7938145", notes="As cited from Qu et al. (2009) by the compiling review."),
    ParamRow("temperature", "temperature_critical_stress_c", "sourced", unit="°C", value_numeric=32.0, context="heat-tolerant cultivars", source_key="heat_stress_review_pmc7938145", notes="As cited from Sato et al. (2006) by the compiling review."),
    ParamRow("temperature", "temperature_critical_stress_c", "sourced", unit="°C", value_numeric=25.0, context="heat-sensitive cultivars", source_key="heat_stress_review_pmc7938145", notes="As cited from Sato et al. (2006) by the compiling review."),

    # --- Humidity ---
    ParamRow("humidity", "humidity_min_pct", "sourced", unit="%", value_min=30.0, value_max=50.0, context="greenhouse tomato, general (not India-specific), stage/light dependent", source_key="shamshiri_2018", notes="Source Table 4 (cultivar 'Caruso') gives finer stage/day-night resolution: ~30-40% observed as a night-time failure floor, general optimal band starts around 50%. ASABE (2015) standard independently cites 60-90% as broadly appropriate -- noted, not merged into this range."),
    ParamRow("humidity", "humidity_max_pct", "sourced", unit="%", value_min=80.0, value_max=100.0, context="greenhouse tomato, general (not India-specific), stage/light dependent", source_key="shamshiri_2018", notes=">90% associated with increased pollen heat-susceptibility; disease risk rises sharply above ~85-90%. The review's authors argue VPD (0.3-1.0 kPa optimal), not RH alone, is the better-founded control variable -- worth reconsidering later."),

    # --- DLI ---
    ParamRow("light", "dli_target_mol_m2_day", "sourced", unit="mol/m2/day", value_min=15.0, value_max=20.0, context="transplant/seedling stage, US greenhouse extension guidance", source_key="purdue_dli_2025", notes="Distinct from the OBSERVED dli_mol_m2_day already recorded per-day in tomato_reference_profile."),
    ParamRow("light", "dli_target_mol_m2_day", "source_needed", unit="mol/m2/day", context="mature production stage", notes="Only commercial LED-grow-light vendor blog sources found for the mature-stage DLI target (indoorfarmsys.com, thriveagritech.com, hortamericas.com, growwithhydroponics.com) -- excluded per this project's sourcing rules. Withheld pending a credible source."),

    # --- Soil: field capacity / wilting point -- context-dependent, not universal ---
    ParamRow("soil", "soil_field_capacity_pct", "context_dependent", unit="%", source_key="nrcs_soil_water_convention", notes="No single value -- inherently soil-texture-specific. Definitional convention: water content at -10 kPa (sandy) to -33 kPa (loam/clay) suction. Illustrative texture-class spread (reference only, not KAVACH's specific unconfirmed soil): sand ~10-15%, clay can exceed 30-40%. Requires a future soil-profile configuration model."),
    ParamRow("soil", "soil_permanent_wilting_point_pct", "context_dependent", unit="%", source_key="nrcs_soil_water_convention", notes="No single value -- texture-specific. Definitional convention: water content at -1500 kPa suction. Requires a future soil-profile configuration model, paired with field capacity above."),

    ParamRow("soil", "soil_bulk_density_g_cm3", "source_needed", unit="g/cm3", notes="No specific credible citation retrieved. General '~1.1-1.6 g/cm3 by texture' figures exist in common knowledge but were not verified against a specific source -- not stored on that basis."),

    ParamRow("soil", "root_zone_depth_cm", "sourced", unit="cm", value_min=70.0, value_max=150.0, context="open field, standard climate conditions (FAO-56 default)", source_key="fao56", notes="FAO-56 Table 22 also gives a no-stress depletion fraction p=0.40 at ETc~5mm/day, noted here for reference. Protected-cultivation systems (containers, grow bags, raised beds) commonly restrict effective root depth well below this open-field figure -- not confirmed for KAVACH's actual (currently unconfigured) growing medium."),

    ParamRow("soil", "soil_available_water_capacity_mm", "derived", unit="mm", notes="AWC = (Field Capacity - Permanent Wilting Point) x root-zone depth (unit conversion via bulk density if working on a mass basis). A computed quantity from three other soil-profile inputs, not an independently stored fact."),

    ParamRow("soil", "soil_texture", "context_dependent", notes="Not applicable as a fixed value -- this is a CONFIGURATION field (the classification of KAVACH's actual polyhouse soil/substrate), not a crop-knowledge fact. No component currently consumes it as crop knowledge. Recommend a future soil-profile configuration model."),

    ParamRow("soil", "soil_ph", "sourced", value_min=6.0, value_max=6.8, context="US home/commercial garden extension guidance, open field/general -- not India- or protected-cultivation-specific", source_key="rutgers_fs678", notes="Corroborated by UNH Extension, UGA CAES, and NC State Extension. Also tolerant down to ~5.5 (a separate tolerance-floor claim, not merged into the optimal range above). Not required for MVP -- nutrient management is explicitly deferred past the water-focused MVP."),

    ParamRow("soil", "soil_ec_ds_m", "sourced", unit="dS/m", value_numeric=2.5, context="saturated soil-paste extract methodology -- differs from fertigation/nutrient-solution EC typically monitored in drip/polyhouse systems", source_key="fao_salt_tolerance", notes="ECe threshold for onset of yield decline; yield decline slope ~9.9% per dS/m above threshold; tomato rated 'Moderately Sensitive'. Not required for MVP -- salinity/nutrient management is explicitly deferred."),

    # --- Nutrient season totals: sourced at per-hectare level, NOT converted to per-plant ---
    ParamRow("nutrient", "n_total_requirement_g_plant_season", "sourced", unit="kg/ha", value_text="200 kg N/ha total season; split 10/40/30/20% across transplanting-establishment / flower-initiation-to-flowering / flowering-to-fruit-set / alternate-day-from-picking stages", context="Indian, hybrid tomato, drip-fertigated -- not confirmed polyhouse-specific", source_key="tnau_fertigation", notes="Parameter name implies g/plant/season but the source gives a per-hectare prescriptive dose; converting requires KAVACH's plant population/spacing, which is not yet configured. This is a prescriptive fertigation dose, distinct from Phase 0's descriptive day-by-day n_demand_g_plant_day -- not silently reconciled with it. Not required for MVP (nutrient optimization deferred)."),
    ParamRow("nutrient", "p2o5_total_requirement_g_plant_season", "sourced", unit="kg/ha", value_text="250 kg P2O5/ha total season, same 10/40/30/20% stage split as N", context="Indian, hybrid tomato, drip-fertigated -- not confirmed polyhouse-specific", source_key="tnau_fertigation", notes="Source table header just says 'P'; interpreted as P2O5 per standard Indian fertilizer-grade convention (19:19:19, 12:61:0, 13:0:45), not stated explicitly in the source text -- inference flagged. Kept explicitly distinct from soil_p_mg_kg (elemental P). Not required for MVP."),
    ParamRow("nutrient", "k2o_total_requirement_g_plant_season", "sourced", unit="kg/ha", value_text="250 kg K2O/ha total season, same 10/40/30/20% stage split as N", context="Indian, hybrid tomato, drip-fertigated -- not confirmed polyhouse-specific", source_key="tnau_fertigation", notes="Same grade-convention inference as P2O5 above. Kept explicitly distinct from soil_k_mg_kg (elemental K). Not required for MVP."),
]


# ---------------------------------------------------------------------------
# Stress conditions (unchanged from Phase 1 -- not part of this phase's
# approved scope; still knowledge-only placeholders)
# ---------------------------------------------------------------------------

_MISSING_STRESS_CONDITIONS: list[tuple[str, str, str, str | None, str]] = [
    ("water_stress", "soil_moisture_pct", "<", "%", "Soil moisture dropping below a to-be-sourced threshold."),
    ("excessive_soil_moisture", "soil_moisture_pct", ">", "%", "Soil moisture rising above a to-be-sourced threshold (overwatering risk)."),
    ("heat_stress", "temperature_c", ">", "°C", "Temperature exceeding a to-be-sourced critical threshold."),
    ("humidity_stress", "humidity_pct", "<", "%", "Humidity outside a to-be-sourced preferred range (placeholder direction: low)."),
    ("nutrient_imbalance", "soil_n_mg_kg", "<", "mg/kg", "Placeholder nutrient-imbalance concept; affected_parameter/operator/threshold not yet sourced."),
]


def seed() -> dict[str, int]:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.query(AgronomicParameter).delete()
        db.query(StressCondition).delete()
        db.query(CropStage).delete()
        db.query(AgronomicSource).delete()

        source_ids: dict[str, int] = {}
        for src in _ALL_SOURCES:
            row = AgronomicSource(
                organization_or_author=src["organization_or_author"],
                title=src["title"],
                publication_year=src["publication_year"],
                source_type=src["source_type"],
                document_reference=src["document_reference"],
                description=src["description"],
                notes=src["notes"],
            )
            db.add(row)
            db.flush()
            source_ids[src["key"]] = row.id

        stage_ids: dict[str, int] = {}
        for stage in _STAGES:
            row = CropStage(
                crop=TOMATO,
                name=stage["name"],
                start_day=stage["start_day"],
                end_day=stage["end_day"],
                description=stage["description"],
                source_id=source_ids[stage["source_key"]],
                notes=None,
            )
            db.add(row)
            db.flush()
            stage_ids[stage["key"]] = row.id

        for p in _PARAMETERS:
            db.add(
                AgronomicParameter(
                    crop=TOMATO,
                    domain=p.domain,
                    parameter_name=p.parameter_name,
                    value_numeric=p.value_numeric,
                    value_min=p.value_min,
                    value_max=p.value_max,
                    value_text=p.value_text,
                    unit=p.unit,
                    stage_id=stage_ids[p.stage_key] if p.stage_key else None,
                    context=p.context,
                    status=p.status,
                    source_id=source_ids[p.source_key] if p.source_key else None,
                    notes=p.notes,
                )
            )

        for stress_type, affected_parameter, operator, unit, description in _MISSING_STRESS_CONDITIONS:
            db.add(
                StressCondition(
                    crop=TOMATO,
                    stress_type=stress_type,
                    affected_parameter=affected_parameter,
                    operator=operator,
                    threshold_value=None,
                    unit=unit,
                    stage_id=None,
                    severity=None,
                    status="missing",
                    source_id=None,
                    description=description,
                    notes=None,
                )
            )

        db.commit()

        counts = {
            "sources": db.query(AgronomicSource).count(),
            "stages": db.query(CropStage).count(),
            "parameters": db.query(AgronomicParameter).count(),
            "stress_conditions": db.query(StressCondition).count(),
        }
    finally:
        db.close()

    return counts


if __name__ == "__main__":
    result = seed()
    print(f"Seeded agronomic knowledge base: {result}")
