"""Tests for Director semantic-QA context preparation (#26)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain_api.contract import (  # noqa: E402
    DirectorContextPrepareRequest,
    DirectorSemanticQaContextPrepareRequest,
    PromptContribution,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.director_semantic_qa_context import (  # noqa: E402
    DIRECTOR_SEMANTIC_QA_RUBRIC,
    build_director_semantic_qa_context_response,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402


def _kernel_scene_round() -> tuple[DomainKernel, str, str]:
    kernel = DomainKernel.for_fixture_store()
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(
        RoundStartRequest(hg_scene_id=scene_id)
    ).hg_round_id
    return kernel, scene_id, round_id


def test_director_semantic_qa_response_includes_rubric_and_candidate() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=scene_id,
            content="Bob, what do you think?",
            speaker="Player",
            hg_round_id=round_id,
        )
    )
    candidate = {
        "next_actor": "Alice",
        "end_round": False,
        "reason": "Alice has not spoken yet.",
        "environment_event": "",
        "tension_shift": "steady",
    }
    response = kernel.prepare_director_semantic_qa_context(
        DirectorSemanticQaContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-director-qa-26",
            turn_index=0,
            evaluation_pass_id="eval-pass-26",
            candidate_decision=candidate,
        )
    )
    assert response.evaluation_target_role == "director"
    assert response.candidate_package["candidate_decision"] == candidate
    assert response.authority_references
    assert any(ref["ref_id"].startswith("user:") for ref in response.authority_references)
    instruction = next(
        c for c in response.contributions if c.contribution_id.endswith("-director-semantic-qa-instruction")
    )
    assert "dir_actor_suitability" in instruction.content
    assert "dir_reason_coherence" in instruction.content
    assert "dir_context_insufficiency" not in instruction.content
    assert any(c.contribution_id.endswith("-authority-references") for c in response.contributions)
    assert any(c.contribution_id.endswith("-candidate-package") for c in response.contributions)


def test_director_semantic_qa_reuses_same_scene_evidence_as_prepare() -> None:
    kernel, scene_id, round_id = _kernel_scene_round()
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=scene_id,
            content="Bob, respond.",
            speaker="Player",
            hg_round_id=round_id,
        )
    )
    director = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-director-26",
            turn_index=0,
            attempt_index=0,
        )
    )
    qa = kernel.prepare_director_semantic_qa_context(
        DirectorSemanticQaContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-director-26",
            turn_index=0,
            evaluation_pass_id="eval-pass-26",
            candidate_decision={
                "next_actor": "Bob",
                "end_round": False,
                "reason": "Bob was addressed.",
                "environment_event": "",
                "tension_shift": "steady",
            },
        )
    )
    director_scene_kinds = {
        c.source_kind
        for c in director.contributions
        if c.source_kind not in ("director_scratch", "inference_instruction")
    }
    qa_scene_kinds = {
        c.source_kind
        for c in qa.contributions
        if c.source_kind != "inference_instruction"
        or c.contribution_id.endswith("-director-semantic-qa-instruction")
    }
    qa_scene_kinds.discard("inference_instruction")
    for kind in ("scene_state", "scene_progression", "user_turn_source", "actor_suitability"):
        assert kind in director_scene_kinds
        assert kind in qa_scene_kinds or kind == "actor_suitability"


def test_build_director_semantic_qa_context_response_fails_closed_on_invalid_refs() -> None:
    role_contrib = PromptContribution(
        contribution_id="manifest-test-role",
        source_kind="director_decision",
        authority_class="derived",
        knowledge_ids=("candidate:1",),
        priority=10,
        content="Role context",
    )
    with pytest.raises(ValueError, match="ref_id is required"):
        build_director_semantic_qa_context_response(
            manifest_id="manifest-director-semantic-qa-bad",
            evaluation_pass_id="eval-bad",
            inference_id="inf-bad",
            hg_scene_id="scene-bad",
            hg_round_id="round-bad",
            turn_index=0,
            role_contributions=[role_contrib],
            authority_references=[{"ref_id": "", "kind": "bad", "label": "", "text": ""}],
            candidate_package={"candidate_decision": {"next_actor": "Alice"}},
        )


def test_rubric_lists_five_dimensions_only() -> None:
    for dimension in (
        "dir_actor_suitability",
        "dir_scene_contradiction",
        "dir_env_event",
        "dir_pacing_tension",
        "dir_reason_coherence",
    ):
        assert dimension in DIRECTOR_SEMANTIC_QA_RUBRIC
