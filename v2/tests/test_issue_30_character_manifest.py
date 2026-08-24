"""Issue #30 — live Character manifest identity, scene conditioning, Director handoff."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_canon_anchors import upsert_canon_anchor  # noqa: E402
from continuity_state import IssueState, IssueStatus  # noqa: E402
from continuity_state_canon import CanonAnchor  # noqa: E402
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    RoundStartRequest,
    ValidationRequest,
)
from domain_api.fixture_store import FixtureStore  # noqa: E402
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.knowledge_write_policy import upsert_canon_anchor_for_test  # noqa: E402
from perception_audibility_constants import REDACTED_PLAYER_TEXT_CONTENT  # noqa: E402


@pytest.fixture
def kernel() -> DomainKernel:
    k = DomainKernel(store=FixtureStore())
    scene = k.create_scene()
    k.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
    return k


def _scene_and_round(kernel: DomainKernel) -> tuple[str, str]:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    assert fixture.rounds
    return fixture.hg_scene_id, fixture.rounds[-1].hg_round_id


def _enrich_alice(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    state = fixture.character_states["Alice"]
    state.description = "A curious artisan"
    state.personality = "Warm but precise"
    state.core_goals = ["finish the commission"]
    state.voice_profile = {"register": "measured"}
    state.reaction_profile = {"default": "observe first"}
    state.speech_fingerprint = {"cadence": "deliberate"}
    state.hidden_agenda = "SECRET_AGENDA_SHOULD_NOT_APPEAR"
    state.set_relationship_context(
        "Bob",
        stance="colleague",
        long_term_goal="earn trust",
    )


def _add_active_issue(kernel: DomainKernel) -> None:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    mgr = fixture.manager
    assert mgr.scene_state is not None
    mgr.issues["issue-trust"] = IssueState(
        issue_id="issue-trust",
        description="Alice owes Bob an explanation",
        participants=["Alice"],
        status=IssueStatus.ACTIVE,
        created_at=datetime.now(timezone.utc),
        pressure_kind="social",
        blocked_what="trust",
        required_next_step="apologize",
    )
    mgr.scene_state.active_issue_ids.append("issue-trust")


def _prepare_character(
    kernel: DomainKernel,
    *,
    director_decision: dict | None = None,
) -> tuple[object, str, str]:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-alice-30",
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            director_decision=director_decision,
        )
    )
    return manifest, hg_scene_id, hg_round_id


def _by_kind(manifest: object, source_kind: str) -> list:
    return [c for c in manifest.contributions if c.source_kind == source_kind]


def test_character_identity_and_expression_project_from_character_state(
    kernel: DomainKernel,
) -> None:
    _enrich_alice(kernel)
    manifest, _, _ = _prepare_character(kernel)
    identity = _by_kind(manifest, "character_identity")
    expression = _by_kind(manifest, "character_expression")
    assert identity
    assert expression
    identity_text = identity[0].content
    assert "curious artisan" in identity_text
    assert "Warm but precise" in identity_text
    assert "finish the commission" in identity_text
    expression_text = expression[0].content
    assert "register=measured" in expression_text
    assert "cadence=deliberate" in expression_text
    assert identity[0].authority_class == "authoritative"


def test_hidden_agenda_not_exposed(kernel: DomainKernel) -> None:
    _enrich_alice(kernel)
    manifest, _, _ = _prepare_character(kernel)
    joined = "\n".join(c.content for c in manifest.contributions)
    assert "SECRET_AGENDA_SHOULD_NOT_APPEAR" not in joined
    assert "hidden agenda" not in joined.lower()


def test_character_relationships_bounded_to_scene_cast(kernel: DomainKernel) -> None:
    _enrich_alice(kernel)
    manifest, _, _ = _prepare_character(kernel)
    relationships = _by_kind(manifest, "character_relationships")
    assert relationships
    assert "Bob" in relationships[0].content
    assert "earn trust" in relationships[0].content


def test_scene_context_and_pressures_reach_character(kernel: DomainKernel) -> None:
    _enrich_alice(kernel)
    _add_active_issue(kernel)
    manifest, _, _ = _prepare_character(kernel)
    scene_context = _by_kind(manifest, "scene_context")
    pressures = _by_kind(manifest, "scene_pressures")
    assert scene_context
    assert "SCENE CONTEXT" in scene_context[0].content
    assert pressures
    assert "issue-trust" in pressures[0].content
    assert "apologize" in pressures[0].content


def test_director_advisory_fields_without_orchestration_mechanics(
    kernel: DomainKernel,
) -> None:
    _enrich_alice(kernel)
    director_decision = {
        "next_actor": "Alice",
        "end_round": False,
        "reason": "The workshop grows tense.",
        "environment_event": "A lamp flickers.",
        "tension_shift": "escalate",
    }
    manifest, _, _ = _prepare_character(kernel, director_decision=director_decision)
    director_context = _by_kind(manifest, "director_context")
    assert director_context
    payload = director_context[0].content
    assert "workshop grows tense" in payload
    assert "lamp flickers" in payload
    assert "escalate" in payload
    assert director_context[0].authority_class == "suggestive"
    assert "advisory only" in payload.lower()
    assert "next_actor" not in payload
    assert "end_round" not in payload


def test_character_profile_stub_replaced_by_identity_lanes(kernel: DomainKernel) -> None:
    _enrich_alice(kernel)
    manifest, _, _ = _prepare_character(kernel)
    kinds = {c.source_kind for c in manifest.contributions}
    assert "character_profile" not in kinds
    assert "character_identity" in kinds
    assert "character_expression" in kinds


def test_identity_duplicate_canon_sources_filtered(kernel: DomainKernel) -> None:
    _enrich_alice(kernel)
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    upsert_canon_anchor(
        fixture.manager,
        CanonAnchor(
            anchor_id="anchor-voice",
            category="character_trait",
            subject="Alice",
            statement="Voice profile: measured and calm.",
            source="character_state.voice_profile",
            established_at=datetime.now(timezone.utc),
        ),
    )
    upsert_canon_anchor_for_test(
        fixture.manager,
        anchor_id="anchor-bridge",
        statement="The bridge is closed.",
    )
    manifest, _, _ = _prepare_character(kernel)
    canon = _by_kind(manifest, "continuity_canon")
    assert canon
    canon_text = canon[0].content.lower()
    assert "bridge is closed" in canon_text
    assert "measured and calm" not in canon_text


def test_inference_instruction_documents_beat_flexibility(kernel: DomainKernel) -> None:
    manifest, _, _ = _prepare_character(kernel)
    instruction = next(c for c in manifest.contributions if c.source_kind == "inference_instruction")
    assert "speech" in instruction.content.lower()
    assert "action-only" in instruction.content.lower() or "action-only" in instruction.content


@pytest.mark.parametrize(
    "beats",
    [
        [{"type": "action", "action": "nods once"}],
        [{"type": "speech", "dialogue": "Hello."}],
        [
            {"type": "action", "action": "steps closer"},
            {"type": "speech", "dialogue": "We should talk."},
        ],
    ],
)
def test_move_schema_accepts_action_speech_and_mixed_beats(
    kernel: DomainKernel,
    beats: list[dict[str, str]],
) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    move = {
        "move_schema_version": 2,
        "beats": beats,
        "motivation": {
            "goal": "connect",
            "tactic": "approach",
            "emotional_driver": "hope",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    result = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-beat-shape",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=move,
            raw_model_output=json.dumps(move),
        )
    )
    assert result.accepted is True


def test_director_manifest_unchanged_by_character_projection(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    director = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-30",
            turn_index=0,
            attempt_index=0,
        )
    )
    director_kinds = {c.source_kind for c in director.contributions}
    assert "scene_setup" in director_kinds
    assert "character_identity" not in director_kinds


def test_authoritative_scene_state_projection_unchanged(kernel: DomainKernel) -> None:
    manifest, _, _ = _prepare_character(kernel)
    scene = _by_kind(manifest, "scene_state")
    assert scene
    assert scene[0].authority_class == "authoritative"


def test_perception_filtering_remains_intact(kernel: DomainKernel) -> None:
    from domain_api.contract import UserTurnRecordRequest  # noqa: E402

    info = kernel.create_session(cast=["Alice", "Bob", "Carol"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id)).hg_round_id
    secret = "NEVER_LEAK_THIS_USER_SECRET"
    kernel.record_user_turn(
        UserTurnRecordRequest(
            hg_session_id=hg_scene_id,
            content=f"Whisper to Bob only: {secret}",
            speaker="Traveler",
            hg_round_id=hg_round_id,
        )
    )
    bob_manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-bob-perception",
            character_id="Bob",
            role="staff",
            turn_index=0,
            attempt_index=0,
        )
    )
    carol_manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-carol-perception",
            character_id="Carol",
            role="witness",
            turn_index=0,
            attempt_index=0,
        )
    )
    bob_trigger = next(c for c in bob_manifest.contributions if c.source_kind == "user_turn_trigger")
    carol_trigger = next(c for c in carol_manifest.contributions if c.source_kind == "user_turn_trigger")
    assert secret in bob_trigger.content
    assert secret not in carol_trigger.content
    assert REDACTED_PLAYER_TEXT_CONTENT in carol_trigger.content


def test_committed_round_moves_remain_in_character_manifest(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-alice-commit",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=PROTOTYPE_VALID_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_VALID_MOVE),
        )
    )
    assert validation.accepted is True
    kernel.commit_move(
        CommitRequest(
            inference_id="inf-alice-commit",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
            expected_turn_index=0,
        )
    )
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-bob-30",
            character_id="Bob",
            role="staff",
            turn_index=1,
            attempt_index=0,
        )
    )
    summary = _by_kind(manifest, "continuity_summary")
    assert summary
    assert "Alice" in summary[0].content


def test_validation_retry_behavior_unchanged(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    invalid_move = {
        "move_schema_version": 2,
        "beats": [],
        "motivation": {
            "goal": "x",
            "tactic": "x",
            "emotional_driver": "x",
            "risk_level": "low",
        },
        "semantic_evaluation": {"decision": "no_covered_change"},
    }
    result = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-invalid",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=invalid_move,
            raw_model_output=json.dumps(invalid_move),
        )
    )
    assert result.accepted is False
