"""Tests for Narrator semantic-QA context preparation (#27)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.modules.authority_reference import validate_finding_citations  # noqa: E402
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    DirectorDecisionValidationRequest,
    NarratorContextPrepareRequest,
    NarratorSemanticQaContextPrepareRequest,
    PromptContribution,
    RoundStartRequest,
)
from domain_api.kernel import DomainKernel, PROTOTYPE_VALID_MOVE  # noqa: E402
from domain_api.narrator_semantic_qa_context import (  # noqa: E402
    NARRATOR_SEMANTIC_QA_DIMENSIONS,
    NARRATOR_SEMANTIC_QA_RUBRIC,
    build_narrator_semantic_qa_context_response,
)


def _kernel_with_commit() -> tuple[DomainKernel, str, str, str, int]:
    kernel = DomainKernel.for_fixture_store()
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
    decision = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-director-27",
            turn_index=0,
            attempt_index=0,
            proposed_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "Alice should act.",
                "tension_shift": "steady",
                "environment_event": "",
            },
        )
    )
    assert decision.accepted is True
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-27",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision=dict(decision.normalized_decision or {}),
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert commit.domain_commit_id is not None
    return kernel, scene_id, round_id, str(commit.domain_commit_id), int(
        commit.continuity_turn_index or 0
    )


def _prepare_response(**overrides):
    kernel, scene_id, round_id, commit_id, turn_index = _kernel_with_commit()
    candidate = "Alice nodded thoughtfully, taking in the workshop."
    raw_output = json.dumps({"presentation_text": candidate})
    request = NarratorSemanticQaContextPrepareRequest(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        inference_id="inf-narrator-27",
        character_id="Alice",
        domain_commit_id=commit_id,
        continuity_turn_index=turn_index,
        evaluation_pass_id="eval-pass-27",
        candidate_presentation=candidate,
        raw_model_output=raw_output,
    )
    for key, value in overrides.items():
        setattr(request, key, value)
    return kernel.prepare_narrator_semantic_qa_context(request)


def test_narrator_semantic_qa_response_includes_rubric_and_candidate() -> None:
    response = _prepare_response()
    assert response.evaluation_target_role == "narrator"
    assert response.character_id == "Alice"
    assert response.candidate_package["candidate_presentation"]
    assert response.candidate_package["raw_model_output"]
    assert any(ref["ref_id"].startswith("commit:") for ref in response.authority_references)
    assert any(ref["ref_id"].startswith("orch:round:") for ref in response.authority_references)
    instruction = next(
        c
        for c in response.contributions
        if c.contribution_id.endswith("-narrator-semantic-qa-instruction")
    )
    assert "nar_attribution_error" in instruction.content
    assert "nar_psychological_invention" in instruction.content
    assert any(c.contribution_id.endswith("-authority-references") for c in response.contributions)
    assert any(c.contribution_id.endswith("-candidate-package") for c in response.contributions)


def test_narrator_prepare_context_accepts_correction_context() -> None:
    kernel, scene_id, round_id, commit_id, turn_index = _kernel_with_commit()
    correction = {
        "source": "semantic_qa",
        "evaluation_pass_id": "eval-pass-27",
        "findings": [{"dimension": "nar_framing_distortion", "severity": "soft"}],
    }
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-narrator-27",
            character_id="Alice",
            domain_commit_id=commit_id,
            continuity_turn_index=turn_index,
            attempt_index=1,
            correction_context=correction,
        )
    )
    kinds = {c.source_kind for c in manifest.contributions}
    assert "semantic_correction" in kinds
    assert manifest.attempt_index == 1


def test_build_narrator_semantic_qa_context_response_fails_closed_on_invalid_refs() -> None:
    role_contrib = PromptContribution(
        contribution_id="manifest-test-role",
        source_kind="committed_move",
        authority_class="authoritative",
        knowledge_ids=("commit:bad",),
        priority=10,
        content="Role context",
    )
    with pytest.raises(ValueError, match="ref_id is required"):
        build_narrator_semantic_qa_context_response(
            manifest_id="manifest-narrator-semantic-qa-bad",
            evaluation_pass_id="eval-bad",
            inference_id="inf-bad",
            hg_scene_id="scene-bad",
            hg_round_id="round-bad",
            turn_index=0,
            character_id="Alice",
            role_contributions=[role_contrib],
            authority_references=[{"ref_id": "", "kind": "bad", "label": "", "text": ""}],
            candidate_package={"candidate_presentation": "test"},
        )


def test_rubric_lists_all_narrator_dimensions() -> None:
    for dimension in NARRATOR_SEMANTIC_QA_DIMENSIONS:
        assert dimension in NARRATOR_SEMANTIC_QA_RUBRIC


def test_narrator_semantic_qa_deduplicated_transport_shape() -> None:
    response = _prepare_response()
    lane_kinds = {
        c.source_kind
        for c in response.contributions
        if not c.contribution_id.endswith(
            ("-authority-references", "-candidate-package", "-narrator-semantic-qa-instruction")
        )
    }
    assert lane_kinds == set()
    assert sum(1 for c in response.contributions if c.source_kind == "inference_instruction") == 2
    assert sum(1 for c in response.contributions if c.source_kind == "active_constraints") == 1


def test_narrator_semantic_qa_candidate_transport_excludes_raw_model_output() -> None:
    response = _prepare_response()
    package = next(
        c for c in response.contributions if c.contribution_id.endswith("-candidate-package")
    )
    assert "raw_model_output" not in package.content
    assert "candidate_presentation" in package.content
    assert response.candidate_package["raw_model_output"]


def test_narrator_semantic_qa_authority_refs_use_whole_commit_without_beat_subdivisions() -> None:
    response = _prepare_response()
    ref_ids = {ref["ref_id"] for ref in response.authority_references}
    commit_refs = [ref_id for ref_id in ref_ids if ref_id.startswith("commit:")]
    assert len(commit_refs) == 1
    assert commit_refs[0].count(":beat:") == 0
    assert commit_refs[0].count(":speech:") == 0


def test_narrator_semantic_qa_hard_finding_citation_still_validates_against_commit_ref() -> None:
    response = _prepare_response()
    commit_ref = next(
        ref["ref_id"]
        for ref in response.authority_references
        if ref["ref_id"].startswith("commit:")
    )
    findings = [
        {
            "dimension": "nar_committed_contradiction",
            "severity": "hard",
            "finding": "contradiction",
            "rationale": "test",
            "authoritative_citation": {"ref_id": commit_ref},
        }
    ]
    validations = validate_finding_citations(findings, list(response.authority_references))
    assert validations[0]["status"] == "valid"


def test_narrator_semantic_qa_environmental_ref_available_for_citation() -> None:
    response = _prepare_response()
    env_refs = [
        ref for ref in response.authority_references if ref["kind"] == "narrator_environment_baseline"
    ]
    assert len(env_refs) == 1
    assert "nar_environmental_contradiction" in NARRATOR_SEMANTIC_QA_RUBRIC


def test_narrator_semantic_qa_transport_content_budget_reduced() -> None:
    response = _prepare_response()
    total_chars = sum(len(c.content) for c in response.contributions)
    legacy_minimal_fixture_budget = 7500
    assert total_chars < legacy_minimal_fixture_budget
    assert total_chars < 6200
