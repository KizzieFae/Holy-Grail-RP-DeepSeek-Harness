"""Issue #54 C2 — role/context module decomposition tests."""

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

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    NarratorContextPrepareRequest,
    NarratorEnvironmentCognitionPrepareRequest,
    OpeningContextPrepareRequest,
    PromptContribution,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.context_substrate import (  # noqa: E402
    auth_projections_to_contributions,
    memory_projections_for_character,
    semantic_correction_contribution,
)
from domain_api.continuity_context_projector import AuthoritativeContextContribution  # noqa: E402
from domain_api.director_context import prepare_director_context  # noqa: E402
from domain_api.kernel import DomainKernel, PROTOTYPE_VALID_MOVE  # noqa: E402
from domain_api.narrator_environment_context import build_environment_knowledge_requests  # noqa: E402
from domain_api.opening_context import prepare_opening_context  # noqa: E402
from domain_api.session_state import initialize_live_session  # noqa: E402
from domain_api.storyteller_contract import advisory_package_to_dict  # noqa: E402
from domain_api.storyteller_round_packaging import validate_storyteller_bind  # noqa: E402
from domain.tests.test_storyteller_s3c_integration import (  # noqa: E402
    _bound_package,
    _scene_round,
)


def _contrib_signature(contrib: PromptContribution) -> tuple:
    return (
        contrib.source_kind,
        contrib.priority,
        contrib.authority_class,
        contrib.contribution_id,
    )


def _manifest_signatures(manifest) -> list[tuple]:
    return [_contrib_signature(c) for c in manifest.contributions]


def test_auth_projections_to_contributions_maps_fields() -> None:
    projections = [
        AuthoritativeContextContribution(
            source_kind="scene_state",
            authority_class="authoritative",
            knowledge_ids=("scene:1",),
            priority=5,
            content="Scene body",
            provenance={"hg_scene_id": "scene-1"},
        )
    ]
    mapped = auth_projections_to_contributions("manifest-test", projections)
    assert len(mapped) == 1
    assert mapped[0].source_kind == "scene_state"
    assert mapped[0].priority == 5
    assert mapped[0].authority_class == "authoritative"
    assert mapped[0].content == "Scene body"
    assert mapped[0].contribution_id == "manifest-test-scene_state"


def test_semantic_correction_contribution_envelope() -> None:
    correction = {"evaluation_pass_id": "pass-1", "hint": "retry"}
    contrib = semantic_correction_contribution(
        "manifest-test",
        correction,
        inference_id="inf-1",
        attempt_index=2,
    )
    assert contrib.source_kind == "semantic_correction"
    assert contrib.authority_class == "suggestive"
    assert contrib.priority == 29
    assert contrib.provenance["attempt_index"] == 2
    assert "pass-1" in contrib.knowledge_ids[0]


def test_memory_projections_for_character_fallback() -> None:
    fixture = initialize_live_session(cast=["Alice"])
    projections = memory_projections_for_character(fixture, "Alice", None)
    assert isinstance(projections, list)


def test_director_module_matches_kernel_facade() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id = kernel.create_scene().hg_scene_id
    round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=scene_id,
            content="Alice, speak.",
            speaker="Player",
            hg_round_id=round_id,
        )
    )
    req = DirectorContextPrepareRequest(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        inference_id="inf-dir-54",
        turn_index=0,
        attempt_index=0,
    )
    via_kernel = kernel.prepare_director_context(req)
    fixture = kernel.store.require(scene_id)
    rnd = next(r for r in fixture.rounds if r.hg_round_id == round_id)
    via_module = prepare_director_context(
        fixture,
        rnd,
        req,
        available_actors=kernel._available_actors(fixture, rnd),
    )
    assert _manifest_signatures(via_kernel) == _manifest_signatures(via_module)
    assert via_kernel.context_completeness == via_module.context_completeness
    kinds = [c.source_kind for c in via_kernel.contributions]
    assert kinds[-1] == "inference_instruction"
    assert "director_scratch" in kinds


def test_character_context_instruction_and_ordering() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-char-54",
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
        )
    )
    kinds = [c.source_kind for c in manifest.contributions]
    assert kinds[-1] == "inference_instruction"
    assert manifest.role == "character"
    assert manifest.character_id == "Alice"


def test_opening_context_manifest_shape() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene = kernel.create_scene()
    req = OpeningContextPrepareRequest(
        hg_session_id=scene.hg_scene_id,
        inference_id="inf-opening-54",
    )
    via_kernel = kernel.prepare_opening_context(req)
    via_module = prepare_opening_context(scene, req)
    assert _manifest_signatures(via_kernel) == _manifest_signatures(via_module)
    assert via_kernel.role == "opening"
    assert via_kernel.hg_round_id == "opening-bootstrap"


def test_storyteller_bind_split_validation_without_mutation() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    package = advisory_package_to_dict(
        _bound_package(hg_round_id=round_id, hg_scene_id=scene_id)
    )
    fixture = kernel.store.require(scene_id)
    rnd = next(r for r in fixture.rounds if r.hg_round_id == round_id)
    validation = validate_storyteller_bind(fixture, rnd, package)
    assert validation.accepted is True
    assert rnd.storyteller_advisory_package is None
    bind = kernel.bind_storyteller_advisory_package(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        package=package,
    )
    assert bind["accepted"] is True
    assert rnd.storyteller_advisory_package is not None


def test_storyteller_bind_rejects_round_mismatch() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    package = advisory_package_to_dict(
        _bound_package(hg_round_id="other-round", hg_scene_id=scene_id)
    )
    bind = kernel.bind_storyteller_advisory_package(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        package=package,
    )
    assert bind["accepted"] is False
    assert bind["reason"] == "round_mismatch"


def test_narrator_environment_context_manifest_priorities() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-env-54",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "Alice acts.",
                "environment_event": "",
                "tension_shift": "steady",
            },
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert commit.domain_commit_id is not None
    req = NarratorEnvironmentCognitionPrepareRequest(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        inference_id="inf-env-cog-54",
        character_id="Alice",
        domain_commit_id=commit.domain_commit_id,
        continuity_turn_index=commit.continuity_turn_index or 1,
    )
    prepared = kernel.prepare_narrator_environment_cognition_context(req)
    manifest = prepared["manifest"]
    kinds = [c.source_kind for c in manifest.contributions]
    assert kinds == [
        "narrator_environment_baseline",
        "triggering_user_context",
        "narrator_environment_cognition",
    ]
    priorities = [c.priority for c in manifest.contributions]
    assert priorities == [17, 19, 30]


def test_build_environment_knowledge_requests_from_n1() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-kar-54",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "Alice acts.",
                "environment_event": "",
                "tension_shift": "steady",
            },
            expected_turn_index=0,
        )
    )
    assert commit.domain_commit_id is not None
    req = NarratorEnvironmentCognitionPrepareRequest(
        hg_scene_id=scene_id,
        hg_round_id=round_id,
        inference_id="inf-kar-54",
        character_id="Alice",
        domain_commit_id=commit.domain_commit_id,
        continuity_turn_index=commit.continuity_turn_index or 1,
    )
    n1_raw = {
        "baseline_sufficient": False,
        "information_needs": [
            {
                "need_id": "need-1",
                "question": "What is behind the door?",
                "category": "environmental_detail",
            }
        ],
        "resolutions": [
            {
                "need_id": "need-1",
                "category": "B1",
                "detail": "behind the door",
            }
        ],
    }
    via_kernel = kernel.build_narrator_environment_knowledge_requests(req, n1_raw=n1_raw)
    fixture = kernel.store.require(scene_id)
    rnd = next(r for r in fixture.rounds if r.hg_round_id == round_id)
    turn_record = next(
        t for t in rnd.character_turns if t.domain_commit_id == commit.domain_commit_id
    )
    via_module = build_environment_knowledge_requests(
        fixture, rnd, turn_record, req, n1_raw=n1_raw
    )
    assert via_kernel == via_module
    assert len(via_kernel) == 1
    json.dumps(via_kernel)


def test_narrator_n2_failure_audit_kernel_orchestration() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-n2-54",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "Alice acts.",
                "environment_event": "",
                "tension_shift": "steady",
            },
            expected_turn_index=0,
        )
    )
    assert commit.domain_commit_id is not None
    audit = {
        "cognition_failed": True,
        "failure_stage": "n1",
        "failure_reason": "timeout",
        "cognition_id": "cog-fail-54",
    }
    kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-narrator-n2-54",
            character_id="Alice",
            domain_commit_id=commit.domain_commit_id,
            continuity_turn_index=commit.continuity_turn_index or 1,
            attempt_index=0,
            cognition_failure=audit,
        )
    )
    fixture = kernel.store.require(scene_id)
    turn_meta = fixture.manager.turn_metadata_by_index.get(
        commit.continuity_turn_index or 1, {}
    )
    stored = turn_meta.get("narrator_environment_audit")
    assert stored is not None
    assert stored["cognition_failed"] is True
    assert stored["failure_reason"] == "timeout"


def test_narrator_context_committed_move_lane() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id = _scene_round(kernel)
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit-nar-54",
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            character_id="Alice",
            validated_move=PROTOTYPE_VALID_MOVE,
            director_decision={
                "next_actor": "Alice",
                "end_round": False,
                "reason": "Alice acts.",
                "environment_event": "",
                "tension_shift": "steady",
            },
            expected_turn_index=0,
        )
    )
    assert commit.domain_commit_id is not None
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-narrator-54",
            character_id="Alice",
            domain_commit_id=commit.domain_commit_id,
            continuity_turn_index=commit.continuity_turn_index or 1,
            attempt_index=0,
        )
    )
    kinds = [c.source_kind for c in manifest.contributions]
    assert "committed_move" in kinds
    assert "narrator_environment_baseline" in kinds
    assert kinds[-1] == "inference_instruction"


def test_no_context_composition_module() -> None:
    domain_api = Path(__file__).resolve().parents[2] / "domain_api"
    assert not (domain_api / "context_composition.py").exists()
