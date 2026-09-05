"""State authority and traceability tests for the V2 Domain API."""

from __future__ import annotations

import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionValidationRequest,
    EligibleActorsRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
    ValidationRequest,
)
from domain_api.http_transport import DomainApiHandler  # noqa: E402
from domain_api.fixture_store import FixtureStore
from domain_api.kernel import (  # noqa: E402
    PROTOTYPE_ALICE_BLUEPRINT_MOVE,
    PROTOTYPE_BOB_MOVE,
    PROTOTYPE_DIRECTOR_DECISION,
    PROTOTYPE_DIRECTOR_DECISION_BOB,
    PROTOTYPE_DIRECTOR_END_ROUND,
    PROTOTYPE_VALID_MOVE,
    DomainKernel,
)
from domain_api.session_history import append_history_entry  # noqa: E402
from player_decomposition_fixtures import build_player_decomposition_for_content  # noqa: E402
from player_entitlement_authority import build_entitlement_authority_snapshot_from_fixture
from player_perceptual_service import (  # noqa: E402
    attach_player_perceptual_metadata,
    validate_player_perceptual_decomposition,
)


def _invalid_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [],
        "motivation": {
            "goal": "x",
            "tactic": "x",
            "emotional_driver": "x",
            "risk_level": "x",
        },
    }


@pytest.fixture
def kernel() -> DomainKernel:
    k = DomainKernel.for_fixture_store()
    scene = k.create_scene()
    k.start_round(RoundStartRequest(hg_scene_id=scene.hg_scene_id))
    return k


def _scene_and_round(kernel: DomainKernel) -> tuple[str, str]:
    fixture = next(iter(kernel.store._scenes.values()))  # noqa: SLF001
    assert fixture.rounds
    return fixture.hg_scene_id, fixture.rounds[-1].hg_round_id


def test_prepare_context_preserves_provenance(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-1",
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
        )
    )
    assert manifest.manifest_id
    assert manifest.inference_id == "inf-1"
    assert manifest.role == "character"
    scene_contrib = next(c for c in manifest.contributions if c.source_kind == "scene_state")
    assert scene_contrib.provenance["hg_scene_id"] == hg_scene_id


def test_director_context_excludes_character_private(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    director = kernel.prepare_director_context(
        DirectorContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-1",
            turn_index=0,
            attempt_index=0,
        )
    )
    character = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-char-1",
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
        )
    )
    director_kinds = {c.source_kind for c in director.contributions}
    character_kinds = {c.source_kind for c in character.contributions}
    assert "character_private" not in director_kinds
    assert "director_scratch" not in character_kinds
    assert "character_private" in character_kinds
    assert "director_scratch" in director_kinds


def test_validate_director_decision_rejects_invalid_actor(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-2",
            turn_index=0,
            attempt_index=0,
            proposed_decision={"next_actor": "Zelda", "end_round": False, "reason": "x"},
            raw_model_output='{"next_actor":"Zelda","end_round":false,"reason":"x"}',
        )
    )
    assert result.accepted is False


def test_validate_director_decision_accepts_valid_actor(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    raw = json.dumps(PROTOTYPE_DIRECTOR_DECISION)
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-3",
            turn_index=0,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION,
            raw_model_output=raw,
        )
    )
    assert result.accepted is True
    assert result.selected_character_id == "Alice"


def test_validation_rejects_invalid_before_commit(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    before = kernel.scene_snapshot(hg_scene_id).turn_counter
    result = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-2",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=before,
            attempt_index=0,
            proposed_move=_invalid_move(),
            raw_model_output=json.dumps(_invalid_move()),
        )
    )
    assert result.accepted is False
    after = kernel.scene_snapshot(hg_scene_id).turn_counter
    assert after == before


def test_proposal_without_commit_does_not_mutate_continuity(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    before = kernel.scene_snapshot(hg_scene_id)
    kernel.record_uncommitted_proposal(hg_scene_id)
    kernel.validate_move(
        ValidationRequest(
            inference_id="inf-3",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=before.turn_counter,
            attempt_index=0,
            proposed_move=PROTOTYPE_VALID_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_VALID_MOVE),
        )
    )
    after = kernel.scene_snapshot(hg_scene_id)
    assert after.turn_counter == before.turn_counter
    assert after.committed_move_count == before.committed_move_count


def test_commit_uses_authoritative_continuity_path(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-4",
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
    assert validation.normalized_move is not None

    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-4",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert commit.continuity_turn_index == 1
    snapshot = kernel.scene_snapshot(hg_scene_id)
    assert snapshot.turn_counter == 1
    assert snapshot.committed_move_count == 1


def _commit_valid_move(kernel: DomainKernel) -> tuple[str, str, str, int]:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-commit",
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
    assert validation.normalized_move is not None
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-commit",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    assert commit.domain_commit_id is not None
    assert commit.continuity_turn_index is not None
    return hg_scene_id, hg_round_id, commit.domain_commit_id, commit.continuity_turn_index


def test_narrator_context_excludes_private_and_director_scratch(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id, domain_commit_id, continuity_turn_index = _commit_valid_move(kernel)
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-narrator-1",
            character_id="Alice",
            domain_commit_id=domain_commit_id,
            continuity_turn_index=continuity_turn_index,
        )
    )
    kinds = {c.source_kind for c in manifest.contributions}
    assert manifest.role == "narrator"
    assert "character_private" not in kinds
    assert "director_scratch" not in kinds
    assert "committed_move" in kinds
    assert "scene_state" in kinds


def test_narrator_context_requires_commit(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    with pytest.raises(ValueError, match="narrator context requires a committed move"):
        kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=hg_scene_id,
                hg_round_id=hg_round_id,
                inference_id="inf-narrator-2",
                character_id="Alice",
                domain_commit_id="hg-commit-missing",
                continuity_turn_index=1,
            )
        )


def test_narrator_context_reflects_committed_move_not_rejected_attempt(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    rejected = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-reject",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=_invalid_move(),
            raw_model_output=json.dumps(_invalid_move()),
        )
    )
    assert rejected.accepted is False
    hg_scene_id, hg_round_id, domain_commit_id, continuity_turn_index = _commit_valid_move(kernel)
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-narrator-3",
            character_id="Alice",
            domain_commit_id=domain_commit_id,
            continuity_turn_index=continuity_turn_index,
        )
    )
    committed = next(c for c in manifest.contributions if c.source_kind == "committed_move")
    assert "nods thoughtfully" in committed.content
    assert "parse_error" not in committed.content


def test_narrator_has_no_commit_path(kernel: DomainKernel) -> None:
    assert not hasattr(kernel, "commit_narration")
    assert not hasattr(kernel, "validate_narration")


def test_director_rejects_already_used_actor(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    _commit_valid_move(kernel)
    fixture = kernel.store.require(hg_scene_id)
    rnd = fixture.rounds[-1]
    assert "Alice" in rnd.actors_used_this_round
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-repeat",
            turn_index=1,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_DECISION,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_DECISION),
        )
    )
    assert result.accepted is False


def test_eligible_actors_excludes_used_cast_members(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    before = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert "Alice" in before.eligible_actors
    assert "Bob" in before.eligible_actors
    _commit_valid_move(kernel)
    after = kernel.eligible_actors(
        EligibleActorsRequest(hg_scene_id=hg_scene_id, hg_round_id=hg_round_id)
    )
    assert "Alice" not in after.eligible_actors
    assert "Bob" in after.eligible_actors
    assert tuple(after.actors_used_this_round) == ("Alice",)


def test_director_accepts_end_round(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    result = kernel.validate_director_decision(
        DirectorDecisionValidationRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-dir-end",
            turn_index=0,
            attempt_index=0,
            proposed_decision=PROTOTYPE_DIRECTOR_END_ROUND,
            raw_model_output=json.dumps(PROTOTYPE_DIRECTOR_END_ROUND),
        )
    )
    assert result.accepted is True
    assert result.selected_character_id is None


def test_bob_context_includes_alice_committed_projection(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    alice_validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-alice-blueprint",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=PROTOTYPE_ALICE_BLUEPRINT_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_ALICE_BLUEPRINT_MOVE),
        )
    )
    assert alice_validation.accepted is True
    assert alice_validation.normalized_move is not None
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-alice-blueprint",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=alice_validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    assert commit.committed is True
    bob_manifest = kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id="inf-bob-projection",
            character_id="Bob",
            role="staff",
            turn_index=commit.continuity_turn_index or 1,
            attempt_index=0,
        )
    )
    summary = next(
        c for c in bob_manifest.contributions if c.source_kind == "continuity_summary"
    )
    assert "places the blueprint on the table" in summary.content
    alice_private = kernel.store.require(hg_scene_id).character_private_secrets["Alice"]
    bob_private = kernel.store.require(hg_scene_id).character_private_secrets["Bob"]
    for contribution in bob_manifest.contributions:
        assert alice_private not in contribution.content
    assert any(bob_private in c.content for c in bob_manifest.contributions)


def _character_manifest(
    kernel: DomainKernel,
    *,
    hg_scene_id: str,
    hg_round_id: str,
    character_id: str,
    turn_index: int = 0,
) -> object:
    return kernel.prepare_context(
        ContextPrepareRequest(
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            inference_id=f"inf-{character_id}-ctx",
            character_id=character_id,
            role="guest",
            turn_index=turn_index,
            attempt_index=0,
        )
    )


def test_prepare_context_includes_transcript_and_trigger_after_user_turn(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice", "Bob"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id)).hg_round_id
    question = "Why is the baseball bat on your shoulder?"
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=hg_scene_id,
            content=question,
            speaker="Traveler",
            hg_round_id=hg_round_id,
        )
    )
    manifest = _character_manifest(
        kernel,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Alice",
    )
    transcript = next(
        c for c in manifest.contributions if c.source_kind == "recent_scene_transcript"
    )
    trigger = next(c for c in manifest.contributions if c.source_kind == "user_turn_trigger")
    assert transcript.authority_class == "derived"
    assert trigger.authority_class == "derived"
    assert question in transcript.content
    assert question in trigger.content
    assert "TRIGGER FOR THIS BEAT" in trigger.content
    assert "RECENT SCENE TRANSCRIPT" in transcript.content


def test_prepare_context_omits_transcript_without_rp_history(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    manifest = _character_manifest(
        kernel,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Alice",
    )
    kinds = {c.source_kind for c in manifest.contributions}
    assert "recent_scene_transcript" not in kinds
    assert "user_turn_trigger" not in kinds


def test_prepare_context_transcript_perception_negative(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice", "Bob", "Carol"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id)).hg_round_id
    secret = "NEVER_LEAK_THIS_USER_SECRET"
    whisper_content = f"Whisper to Bob only: {secret}"
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=hg_scene_id,
            content=whisper_content,
            speaker="Traveler",
            hg_round_id=hg_round_id,
            player_decomposition=build_player_decomposition_for_content(
                whisper_content,
                scope="directed",
                characters=["Bob"],
            ),
        )
    )
    bob_manifest = _character_manifest(
        kernel,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Bob",
    )
    carol_manifest = _character_manifest(
        kernel,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Carol",
    )
    bob_trigger = next(
        c for c in bob_manifest.contributions if c.source_kind == "user_turn_trigger"
    )
    carol_trigger = next(
        (c for c in carol_manifest.contributions if c.source_kind == "user_turn_trigger"),
        None,
    )
    assert secret in bob_trigger.content
    assert carol_trigger is None or secret not in carol_trigger.content


def test_prepare_context_transcript_bounded_at_sixteen(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    fixture = kernel.store.require(hg_scene_id)
    for index in range(20):
        content = f"User line {index}"
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Traveler",
            decomposition=build_player_decomposition_for_content(content),
        )
        snapshot = build_entitlement_authority_snapshot_from_fixture(fixture)
        metadata = attach_player_perceptual_metadata(
            {"speaker": "Traveler"},
            record=record,
            validation_audit=audit,
            entitlement_authority_snapshot=snapshot,
        )
        append_history_entry(
            fixture.rp_history,
            kind="user",
            content=content,
            actor_id="Traveler",
            metadata=metadata,
        )
    manifest = _character_manifest(
        kernel,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Alice",
    )
    transcript = next(
        c for c in manifest.contributions if c.source_kind == "recent_scene_transcript"
    )
    assert transcript.provenance["transcript_message_count"] == 16
    assert "User line 4" in transcript.content
    assert "User line 0" not in transcript.content


def test_prepare_context_continuity_summary_unaffected(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    alice_validation = kernel.validate_move(
        ValidationRequest(
            inference_id="inf-alice-continuity",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            role="guest",
            turn_index=0,
            attempt_index=0,
            proposed_move=PROTOTYPE_ALICE_BLUEPRINT_MOVE,
            raw_model_output=json.dumps(PROTOTYPE_ALICE_BLUEPRINT_MOVE),
        )
    )
    assert alice_validation.accepted is True
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-alice-continuity",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            character_id="Alice",
            validated_move=alice_validation.normalized_move,
            director_decision=PROTOTYPE_DIRECTOR_DECISION,
            expected_turn_index=0,
        )
    )
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=hg_scene_id,
            content="Follow-up question about the blueprint.",
            speaker="Traveler",
            hg_round_id=hg_round_id,
        )
    )
    manifest = _character_manifest(
        kernel,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        character_id="Bob",
        turn_index=commit.continuity_turn_index or 1,
    )
    summary = next(c for c in manifest.contributions if c.source_kind == "continuity_summary")
    trigger = next(c for c in manifest.contributions if c.source_kind == "user_turn_trigger")
    assert "places the blueprint on the table" in summary.content
    assert "Follow-up question" in trigger.content
    assert trigger.source_kind != "continuity_summary"


def test_http_transport_round_trip(kernel: DomainKernel) -> None:
    hg_scene_id, hg_round_id = _scene_and_round(kernel)
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/director/context/prepare",
            data=json.dumps(
                {
                    "hg_scene_id": hg_scene_id,
                    "hg_round_id": hg_round_id,
                    "inference_id": "inf-http",
                    "turn_index": 0,
                    "attempt_index": 0,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        kinds = {c["source_kind"] for c in payload["contributions"]}
        assert "character_private" not in kinds
    finally:
        server.shutdown()
        server.server_close()


def test_http_character_context_serializes_transcript_contributions(kernel: DomainKernel) -> None:
    info = kernel.create_session(cast=["Alice", "Bob"])
    hg_scene_id = info.hg_scene_id
    hg_round_id = kernel.start_round(RoundStartRequest(hg_scene_id=hg_scene_id)).hg_round_id
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=hg_scene_id,
            content="Can you hear me?",
            speaker="Traveler",
            hg_round_id=hg_round_id,
        )
    )
    handler = type("H", (DomainApiHandler,), {"kernel": kernel})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        import urllib.request

        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/v1/context/prepare",
            data=json.dumps(
                {
                    "hg_scene_id": hg_scene_id,
                    "hg_round_id": hg_round_id,
                    "inference_id": "inf-http-char",
                    "character_id": "Alice",
                    "role": "guest",
                    "turn_index": 0,
                    "attempt_index": 0,
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        kinds = {c["source_kind"] for c in payload["contributions"]}
        assert "recent_scene_transcript" in kinds
        assert "user_turn_trigger" in kinds
        transcript = next(
            c for c in payload["contributions"] if c["source_kind"] == "recent_scene_transcript"
        )
        assert transcript["authority_class"] == "derived"
    finally:
        server.shutdown()
        server.server_close()
