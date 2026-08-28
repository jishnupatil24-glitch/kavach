"""
Shared status vocabulary for agronomic knowledge records.

sourced        - directly supported by a documented agricultural source
assumption     - a modelling assumption, not presented as scientific fact
missing        - a parameter later phases may need, with no source yet
source_needed  - a specific candidate value exists (e.g. surfaced in
                 discussion) but no verifiable source has been confirmed,
                 so the value itself is withheld
derived        - a computed quantity (e.g. ETo, ETc), never a fixed
                 lookup fact; value fields stay NULL permanently, the
                 computation belongs to a future calculation service
context_dependent - a real parameter that is site/config-specific (e.g.
                 soil field capacity depends on soil texture); value
                 fields stay NULL, a source_id may still cite the
                 definitional source even with no single number stored
project_defined - a KAVACH-authored prototype operational/decision-engine
                 rule (e.g. a Phase 5 eligibility gate), never presented
                 as an externally sourced agronomic fact; source_id stays
                 NULL unless a real external source genuinely supports
                 that specific parameter -- notes must carry the exact
                 disclaimer "KAVACH project-defined prototype rule --
                 not an externally sourced agronomic fact."
"""
AGRONOMIC_STATUS_VALUES = (
    "sourced",
    "assumption",
    "missing",
    "source_needed",
    "derived",
    "context_dependent",
    "project_defined",
)
