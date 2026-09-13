"""Tests for Player-authorship authority projection (#157)."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.player_authorship_authority import (  # noqa: E402
    PLAYER_AUTHORSHIP_GUARDRAIL_ID,
    TIER1_PLAYER_ORIGIN_KINDS,
    build_player_authorship_guardrail,
    merge_player_authorship_authority_references,
    project_player_authority_references,
)


def test_guardrail_id_and_tier1_origins() -> None:
    guardrail = build_player_authorship_guardrail()
    assert guardrail["ref_id"] == PLAYER_AUTHORSHIP_GUARDRAIL_ID
    assert guardrail["authority_class"] == "authoritative"
    assert "user_post" in TIER1_PLAYER_ORIGIN_KINDS
    assert "character_card" in TIER1_PLAYER_ORIGIN_KINDS


def test_project_user_post_and_decomposition() -> None:
    class _Fixture:
        setup_snapshot = {}
        rp_history = [
            {
                "entry_id": "user-1",
                "sequence_index": 1,
                "kind": "user",
                "content": "Kizzie shivered once in the cold draft.",
                "metadata": {
                    "player_decomposition": {
                        "semantic_decomposition": {
                            "units": [{"kind": "observable_event", "text": "shivered"}],
                        },
                    },
                },
            },
        ]

    refs = project_player_authority_references(_Fixture(), player_character="Kizzie")
    ref_ids = {ref["ref_id"] for ref in refs}
    assert "player_fact:user_post:user-1" in ref_ids
    assert "player_fact:decomposition:user-1" in ref_ids
    post = next(ref for ref in refs if ref["ref_id"] == "player_fact:user_post:user-1")
    assert post["provenance"]["origin_kind"] == "user_post"


def test_merge_inserts_guardrail_first_and_dedupes() -> None:
    class _Fixture:
        setup_snapshot = {}
        rp_history = []

    merged = merge_player_authorship_authority_references(
        [{"ref_id": "perception_fact:scene:present_characters", "kind": "perception_fact",
          "authority_class": "authoritative", "label": "x", "text": "y"}],
        _Fixture(),
    )
    assert merged[0]["ref_id"] == PLAYER_AUTHORSHIP_GUARDRAIL_ID
    assert merged[1]["ref_id"] == "perception_fact:scene:present_characters"
