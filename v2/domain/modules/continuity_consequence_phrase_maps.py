"""Static phrase and implication maps for continuity consequence categories (Issue #149 Slice 1).

Templates keyed by ``ConsequenceCategory``; state-change strings are expanded with
``acting_character``. No classification or promotion logic — data only.
"""

from continuity_state import ConsequenceCategory

# Category → state_change phrase template (single ``{acting_character}`` placeholder).
CATEGORY_STATE_CHANGE_PHRASES: dict[ConsequenceCategory, str] = {
    ConsequenceCategory.AUTHORITY_ASSERTED: (
        "{acting_character} asserted authority or control."
    ),
    ConsequenceCategory.AUTHORITY_CHALLENGED: (
        "{acting_character} challenged existing authority."
    ),
    ConsequenceCategory.TERRITORIAL_CLAIM: (
        "{acting_character} claimed presence in contested space."
    ),
    ConsequenceCategory.TERRITORIAL_DENIAL: (
        "{acting_character} denied another's right to remain."
    ),
    ConsequenceCategory.MEDIATION_ATTEMPTED: (
        "{acting_character} attempted to mediate the conflict."
    ),
    ConsequenceCategory.INTERCEPTION: (
        "{acting_character} rejected mediation and reasserted control."
    ),
    ConsequenceCategory.ARRIVAL: "{acting_character} arrived in the scene.",
    ConsequenceCategory.EXIT: "{acting_character} left the immediate scene.",
    ConsequenceCategory.REPOSITIONING: (
        "{acting_character} repositioned physically in contested space."
    ),
    ConsequenceCategory.REFUSAL: (
        "{acting_character} refused the current demand, request, or proposed course of "
        "action."
    ),
    ConsequenceCategory.AGREEMENT: "{acting_character} agreed or accepted a proposal.",
    ConsequenceCategory.COMMITMENT: "{acting_character} committed to a future action.",
    ConsequenceCategory.ACCESS_GRANTED: "{acting_character} granted access or permission.",
    ConsequenceCategory.ACCESS_DENIED: "{acting_character} denied access or blocked entry.",
    ConsequenceCategory.REVELATION: (
        "{acting_character} revealed significant information."
    ),
    ConsequenceCategory.CONCEALMENT: "{acting_character} concealed or hid information.",
    ConsequenceCategory.PHYSICAL_STATE_SET: (
        "{acting_character} established or changed a concrete physical detail in the scene."
    ),
    ConsequenceCategory.MEDICAL_STATE_SET: (
        "{acting_character} applied or confirmed a hands-on medical or first-aid detail."
    ),
}


CATEGORY_ACTIONABLE_IMPLICATIONS: dict[ConsequenceCategory, str] = {
    ConsequenceCategory.AUTHORITY_ASSERTED: (
        "Authority dynamics are now contested and must be resolved."
    ),
    ConsequenceCategory.AUTHORITY_CHALLENGED: (
        "The challenged party must respond or cede control."
    ),
    ConsequenceCategory.TERRITORIAL_CLAIM: "Territorial boundaries are now disputed.",
    ConsequenceCategory.TERRITORIAL_DENIAL: (
        "The targeted character must exit, challenge back, or submit."
    ),
    ConsequenceCategory.MEDIATION_ATTEMPTED: (
        "The mediator temporarily controls the interaction flow."
    ),
    ConsequenceCategory.INTERCEPTION: (
        "Mediation failed; direct confrontation is resuming."
    ),
    ConsequenceCategory.ARRIVAL: "Others must account for the new arrival's presence.",
    ConsequenceCategory.EXIT: "The remaining cast must proceed without the departed character.",
    ConsequenceCategory.ESCALATION: (
        "Tension is increasing; pressure mounts on all parties."
    ),
    ConsequenceCategory.DEESCALATION: (
        "Tension is reducing; opportunity for resolution or rest."
    ),
    ConsequenceCategory.REFUSAL: (
        "The cast must respond to the refusal or choose a different course."
    ),
    ConsequenceCategory.AGREEMENT: (
        "The agreed course can now move from debate to execution."
    ),
    ConsequenceCategory.COMMITMENT: (
        "The committed action creates future obligation and pressure."
    ),
    ConsequenceCategory.ACCESS_GRANTED: (
        "The granted access can be used immediately by the recipient."
    ),
    ConsequenceCategory.ACCESS_DENIED: (
        "The denied party must find leverage or alternate route."
    ),
    ConsequenceCategory.REVELATION: (
        "Others can now act on the newly revealed information."
    ),
    ConsequenceCategory.PHYSICAL_STATE_SET: (
        "A physical object or placement detail is now part of shared scene reality."
    ),
    ConsequenceCategory.MEDICAL_STATE_SET: (
        "A medical or stabilization detail is now part of shared scene reality."
    ),
}


def category_state_change_phrases(acting_character: str) -> dict[ConsequenceCategory, str]:
    """Expand state-change templates for this actor (same strings as legacy f-strings)."""
    return {
        cat: tmpl.format(acting_character=acting_character)
        for cat, tmpl in CATEGORY_STATE_CHANGE_PHRASES.items()
    }
