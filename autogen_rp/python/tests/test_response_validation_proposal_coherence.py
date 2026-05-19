"""Unit tests for proposal structural coherence (#231)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "rp_app"))

from response_validation_proposal_coherence import (
    PROPOSAL_COHERENCE_TAG,
    PROPOSAL_INCONSISTENT_TAG,
    PROPOSAL_SCOPE_TAG,
    is_proposal_rejection_reason,
    validate_proposal_structural_coherence,
)


def _v2_move(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "content": "stays seated"}],
        "motivation": "test",
    }
    base.update(extra)
    return base


def test_structural_passes_without_proposals() -> None:
    ok, reason, code = validate_proposal_structural_coherence(
        _v2_move(), acting_character="Alice"
    )
    assert ok is True
    assert reason == ""
    assert code == ""


def test_scope_non_self_rejects() -> None:
    move = _v2_move(
        semantic_proposals=[
            {"character": "Bob", "kind": "off_focal", "operation": None}
        ]
    )
    ok, reason, code = validate_proposal_structural_coherence(
        move, acting_character="Alice"
    )
    assert ok is False
    assert reason.startswith(PROPOSAL_SCOPE_TAG)
    assert code == "scope_non_self"


def test_off_focal_and_reentry_conflict() -> None:
    move = _v2_move(
        semantic_proposals=[
            {"character": "Alice", "kind": "off_focal"},
            {"character": "Alice", "kind": "reentry"},
        ]
    )
    ok, reason, code = validate_proposal_structural_coherence(
        move, acting_character="Alice"
    )
    assert ok is False
    assert reason.startswith(PROPOSAL_INCONSISTENT_TAG)
    assert code == "proposal_set_conflict"


def test_excursion_open_close_conflict() -> None:
    move = _v2_move(
        semantic_proposals=[
            {
                "character": "Alice",
                "kind": "excursion_lifecycle",
                "operation": "open",
            },
            {
                "character": "Alice",
                "kind": "excursion_lifecycle",
                "operation": "close",
            },
        ]
    )
    ok, reason, code = validate_proposal_structural_coherence(
        move, acting_character="Alice"
    )
    assert ok is False
    assert code == "proposal_set_conflict"


def test_is_proposal_rejection_reason_tags() -> None:
    assert is_proposal_rejection_reason(f"{PROPOSAL_SCOPE_TAG} x")
    assert is_proposal_rejection_reason(f"{PROPOSAL_INCONSISTENT_TAG} x")
    assert is_proposal_rejection_reason(f"{PROPOSAL_COHERENCE_TAG} x")
    assert not is_proposal_rejection_reason("[DUPLICATE] x")
