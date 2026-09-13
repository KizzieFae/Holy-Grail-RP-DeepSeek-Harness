"""Tests for player action completion authority contract (#193)."""

from __future__ import annotations

import sys
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.player_action_completion_authority import (  # noqa: E402
    PLAYER_ACTION_COMPLETION_GUARDRAIL_ID,
    build_player_action_completion_guardrail,
    merge_player_action_completion_authority_references,
    project_player_action_completion_generation_guidance,
)


def test_guardrail_contract_is_declarative_only() -> None:
    guardrail = build_player_action_completion_guardrail()
    assert guardrail["ref_id"] == PLAYER_ACTION_COMPLETION_GUARDRAIL_ID
    text = str(guardrail["text"])
    assert "R16" in text
    assert "location_entry_outcome" in text
    assert "R02b" in text


def test_merge_inserts_guardrail_without_duplication() -> None:
    base = [{"ref_id": "continuity_fact:scene:location", "kind": "continuity_fact"}]
    merged = merge_player_action_completion_authority_references(base)
    ref_ids = [ref["ref_id"] for ref in merged]
    assert ref_ids[0] == PLAYER_ACTION_COMPLETION_GUARDRAIL_ID
    assert ref_ids.count(PLAYER_ACTION_COMPLETION_GUARDRAIL_ID) == 1
    assert "continuity_fact:scene:location" in ref_ids


def test_generation_guidance_preserves_npc_initiative() -> None:
    guidance = project_player_action_completion_generation_guidance()
    assert "multi-beat" in guidance
    assert "threaten" in guidance
    assert "grab" in guidance
    assert "permission" in guidance
