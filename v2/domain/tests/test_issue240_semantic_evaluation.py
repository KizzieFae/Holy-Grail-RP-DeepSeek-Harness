"""Issue #240 v1_next5 semantic_evaluation ingress and normalization."""

from __future__ import annotations

import pytest

from character_move_ingress import ingest_character_move_json_object
from issue240_semantic_evaluation import (
    normalize_issue240_semantic_evaluation_for_continuity,
    validate_semantic_evaluation_block,
)


def _minimal_v2(**extra: object) -> dict:
    base = {
        "move_schema_version": 2,
        "beats": [{"type": "action", "action": "She looked away."}],
        "motivation": {
            "goal": "stay guarded",
            "tactic": "minimal reply",
            "emotional_driver": "irritation",
            "risk_level": "low",
        },
    }
    base.update(extra)
    return base


@pytest.fixture(autouse=True)
def _enable_semantic_eval_ingress(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RP_ISSUE240_PROMPT_TOPOLOGY", raising=False)


def test_semantic_evaluation_enabled_by_default_without_env() -> None:
    from issue240_semantic_evaluation import issue240_semantic_evaluation_enabled

    assert issue240_semantic_evaluation_enabled() is True


def test_semantic_evaluation_enabled_for_participation_calibration_a(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from issue240_semantic_evaluation import issue240_semantic_evaluation_enabled

    monkeypatch.setenv(
        "RP_ISSUE240_PROMPT_TOPOLOGY",
        "v1_next7_participation_calibration_a",
    )
    assert issue240_semantic_evaluation_enabled() is True


def test_semantic_evaluation_enabled_for_proposal_schema_a(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from issue240_semantic_evaluation import issue240_semantic_evaluation_enabled

    monkeypatch.setenv(
        "RP_ISSUE240_PROMPT_TOPOLOGY",
        "v1_next7_proposal_schema_a",
    )
    assert issue240_semantic_evaluation_enabled() is True


def test_semantic_evaluation_enabled_for_participation_boundary_b(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from issue240_semantic_evaluation import issue240_semantic_evaluation_enabled

    monkeypatch.setenv(
        "RP_ISSUE240_PROMPT_TOPOLOGY",
        "v1_next7_participation_boundary_b",
    )
    assert issue240_semantic_evaluation_enabled() is True


def test_semantic_evaluation_enabled_for_participation_boundary_b_clean(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from issue240_semantic_evaluation import issue240_semantic_evaluation_enabled

    monkeypatch.setenv(
        "RP_ISSUE240_PROMPT_TOPOLOGY",
        "v1_next7_participation_boundary_b_clean",
    )
    assert issue240_semantic_evaluation_enabled() is True


def test_semantic_evaluation_no_covered_change_valid() -> None:
    move = _minimal_v2(
        semantic_evaluation={"decision": "no_covered_change"},
    )
    out, err = ingest_character_move_json_object(move)
    assert err == ""
    assert out is not None
    assert out.get("semantic_evaluation") == {"decision": "no_covered_change"}


def test_semantic_evaluation_covered_change_requires_proposals() -> None:
    move = _minimal_v2(
        semantic_evaluation={"decision": "covered_change"},
    )
    out, err = ingest_character_move_json_object(move)
    assert out is None
    assert "proposals must be a non-empty array" in err


def test_semantic_evaluation_rejects_empty_root_proposals_array() -> None:
    move = _minimal_v2(semantic_proposals=[])
    out, err = ingest_character_move_json_object(move)
    assert out is None
    assert "semantic_proposals: [] is not allowed" in err


def test_semantic_evaluation_mutually_exclusive_with_root_proposals() -> None:
    move = _minimal_v2(
        semantic_evaluation={"decision": "no_covered_change"},
        semantic_proposals=[{"kind": "off_focal", "character": "Willow"}],
    )
    out, err = ingest_character_move_json_object(move)
    assert out is None
    assert "mutually exclusive" in err


def test_normalize_promotes_covered_change_proposals() -> None:
    move = _minimal_v2(
        semantic_evaluation={
            "decision": "covered_change",
            "proposals": [{"kind": "off_focal", "character": "Willow"}],
        },
    )
    norm = normalize_issue240_semantic_evaluation_for_continuity(move)
    assert "semantic_evaluation" not in norm
    assert norm["semantic_proposals"] == [{"kind": "off_focal", "character": "Willow"}]


def test_normalize_strips_proposals_on_no_covered_change() -> None:
    move = _minimal_v2(
        semantic_evaluation={"decision": "no_covered_change"},
        semantic_proposals=[{"kind": "off_focal", "character": "Willow"}],
    )
    norm = normalize_issue240_semantic_evaluation_for_continuity(move)
    assert "semantic_evaluation" not in norm
    assert "semantic_proposals" not in norm


def test_validate_semantic_evaluation_block_rejects_unknown_decision() -> None:
    err = validate_semantic_evaluation_block({"decision": "maybe"})
    assert "covered_change or no_covered_change" in err
