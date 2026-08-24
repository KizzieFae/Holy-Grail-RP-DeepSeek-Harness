"""Issue #23 deterministic Director auxiliary-output contract."""

from director_decision_contract import (
    canonicalize_environment_event,
    normalize_environment_event,
    normalize_tension_shift,
)
from continuity_event_promotion_policy import determine_significance


def test_tension_shift_closed_contract() -> None:
    assert normalize_tension_shift(" escalate ") == "escalate"
    assert normalize_tension_shift("SOFTEN") == "soften"
    assert normalize_tension_shift("steady") == "steady"


def test_tension_shift_legacy_invalid_and_malformed_are_steady() -> None:
    for value in ("unsettle", "hold", "reveal", "slightly raised", "", None, 7):
        assert normalize_tension_shift(value) == "steady"


def test_unsettle_no_longer_has_shadow_event_significance() -> None:
    assert determine_significance([], "medium", "unsettle", "", "") == "minor"
    assert determine_significance([], "medium", "escalate", "", "") == "major"


def test_environment_canonicalization_is_exact_not_semantic() -> None:
    assert canonicalize_environment_event("  ＣＨＩＭＥ\tRings  ") == "chime rings"
    assert canonicalize_environment_event("Chime, rings.") == "chime, rings."
    assert canonicalize_environment_event({"event": "rain"}) == ""


def test_environment_duplicate_blanks_without_fuzzy_matching() -> None:
    recent = ["A chime rings inside."]
    assert (
        normalize_environment_event(
            "  A CHIME   rings inside. ",
            recent_committed_events=recent,
        )
        == ""
    )
    assert (
        normalize_environment_event(
            "The chime sounds again.",
            recent_committed_events=recent,
        )
        == "The chime sounds again."
    )


def test_environment_unique_text_preserves_original_wording() -> None:
    proposed = "Rain begins against the windows."
    assert (
        normalize_environment_event(
            proposed,
            recent_committed_events=["A chime rings inside."],
        )
        == proposed
    )
