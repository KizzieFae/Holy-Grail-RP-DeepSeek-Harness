"""Parity-focused tests for ``director_reason_projection`` (GitHub #210 C-A)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from director_reason_projection import (
    finalize_reason_with_display_substitution,
    merge_addressee_alignment_reason,
    merge_participation_fairness_reason,
    merge_progression_override_reason,
    merge_turn_selection_diagnostics_reason,
)
from semantic_validation import substitute_agent_keys_with_display_names


def test_merge_progression_override_reason_matches_formula() -> None:
    seed = "pick because tension"
    out = merge_progression_override_reason(seed, "Ayame", "Celina")
    expected = (
        f"{seed} | Progression override from Ayame to Celina".strip(" |")
    )
    assert out == expected


def test_merge_participation_fairness_nonempty_previous() -> None:
    seed = "prior"
    unheard = "Hannah_Lovelace"
    out = merge_participation_fairness_reason(seed, unheard)
    expected_note = (
        f"Spotlight fairness: rotate to {unheard} "
        "(present participant not yet heard this response cycle)"
    )
    assert out == f"{seed} | {expected_note}".strip(" |")


def test_merge_participation_fairness_empty_previous_matches_spotlight() -> None:
    unheard = "Mira"
    out = merge_participation_fairness_reason("", unheard)
    assert out.startswith("Spotlight fairness:")
    assert unheard in out


def test_merge_addressee_alignment_reason_prior_nonempty() -> None:
    merged = merge_addressee_alignment_reason("director rationale", "Ayame", "Celina")
    assert "| Addressee alignment (progression gate): Ayame -> Celina" in merged
    assert merged.startswith("director rationale")


def test_merge_addressee_alignment_reason_prior_empty_suffix_strip() -> None:
    merged = merge_addressee_alignment_reason("", "Ayame", "Celina")
    assert merged.startswith("| Addressee alignment")


def test_merge_turn_selection_diagnostics_reason() -> None:
    merged = merge_turn_selection_diagnostics_reason(
        "base note",
        ["Validation: a; b", "[routing block]"],
    )
    assert "Validation: a; b" in merged
    assert "[routing block]" in merged


def test_stacked_finalize_path_order_stable() -> None:
    assembled = merge_addressee_alignment_reason(
        "start", "speaker_a", "speaker_b"
    )
    assembled = merge_progression_override_reason(
        assembled, "speaker_b", "speaker_c"
    )
    assembled = merge_participation_fairness_reason(assembled, "speaker_d")
    assembled = merge_turn_selection_diagnostics_reason(assembled, ["Validation: diag"])
    assert "start" in assembled
    assert "speaker_d" in assembled
    assert "Validation: diag" in assembled


def test_finalize_reason_with_display_substitution() -> None:
    assembled = "Celina nods toward Ayame"
    out = finalize_reason_with_display_substitution(
        assembled,
        substitute_display_names=lambda t: substitute_agent_keys_with_display_names(
            t,
            participant_names=["Celina", "Ayame"],
            display_name_for_key=lambda k: (
                "Ms Celina"
                if k == "Celina"
                else ("Ms Ayame" if k == "Ayame" else k)
            ),
        ),
    )
    assert "Ms Celina" in out and "Ayame" in out  # Celina substituted; Ayame untouched
