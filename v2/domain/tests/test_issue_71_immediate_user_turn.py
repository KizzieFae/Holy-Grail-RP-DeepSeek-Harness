"""Issue #71 — immediate user-turn Narrator cognition input tests."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from continuity_state import PublicEvent  # noqa: E402
from continuity_state_occurrence_evidence import (  # noqa: E402
    OccurrenceEvidence,
    TriggeringUser,
)
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    NarratorContextPrepareRequest,
    NarratorEnvironmentCognitionPrepareRequest,
    PlayerSkipRecordRequest,
    RoundStartRequest,
    UserTurnRecordRequest,
)
from domain_api.kernel import DomainKernel, PROTOTYPE_VALID_MOVE  # noqa: E402
from domain_api.narrator_environment_cognition import (  # noqa: E402
    build_cognition_context_payload,
    extract_triggering_user_context,
)
from domain_api.session_history import (  # noqa: E402
    IMMEDIATE_USER_TURN_SOURCE,
    project_immediate_user_turn_context,
)
from domain_api.session_state import CharacterTurnRecord, initialize_live_session  # noqa: E402


def _commit_after_user(kernel: DomainKernel, *, user_content: str) -> tuple[str, str, str, int]:
    created = kernel.create_session(cast=["Alice"])
    scene_id = created.hg_scene_id
    rnd = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id))
    round_id = rnd.hg_round_id
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=scene_id,
            content=user_content,
            speaker="Player",
            hg_round_id=round_id,
        )
    )
    commit = kernel.commit_move(
        CommitRequest(
            inference_id="inf-71-commit",
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
    assert commit.committed and commit.domain_commit_id
    return scene_id, round_id, commit.domain_commit_id, commit.continuity_turn_index or 1


def test_immediate_user_turn_in_cognition_payload_without_public_event() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id, commit_id, _turn_idx = _commit_after_user(
        kernel,
        user_content="Kizzie looked up at the numbers above the door.",
    )
    fixture = kernel.store.require(scene_id)
    rnd = next(r for r in fixture.rounds if r.hg_round_id == round_id)
    turn = next(t for t in rnd.character_turns if t.domain_commit_id == commit_id)
    payload = build_cognition_context_payload(fixture, rnd, turn)
    immediate = payload["immediate_user_turn"]
    assert immediate is not None
    assert immediate["source"] == IMMEDIATE_USER_TURN_SOURCE
    assert "numbers above the door" in immediate["content"]
    assert payload["triggering_user"] is None
    assert extract_triggering_user_context(fixture, turn) is None


def test_immediate_user_turn_in_env_cognition_manifest_without_public_event() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id, commit_id, turn_idx = _commit_after_user(
        kernel,
        user_content="She took a moment to look around the foyer.",
    )
    manifest = kernel.prepare_narrator_environment_cognition_context(
        NarratorEnvironmentCognitionPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-71-env",
            character_id="Alice",
            domain_commit_id=commit_id,
            continuity_turn_index=turn_idx,
        )
    )["manifest"]
    kinds = {c.source_kind for c in manifest.contributions}
    assert "immediate_user_turn_context" in kinds
    immediate = next(
        c for c in manifest.contributions if c.source_kind == "immediate_user_turn_context"
    )
    body = json.loads(immediate.content)
    assert "look around" in body["immediate_user_turn"]["content"]
    assert immediate.provenance.get("trigger_entry_id")
    trigger = next(c for c in manifest.contributions if c.source_kind == "triggering_user_context")
    assert json.loads(trigger.content)["triggering_user"] is None


def test_immediate_user_turn_in_main_narrator_manifest_without_public_event() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id, commit_id, turn_idx = _commit_after_user(
        kernel,
        user_content="Kizzie waited quietly, saying nothing.",
    )
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-71-narr",
            character_id="Alice",
            domain_commit_id=commit_id,
            continuity_turn_index=turn_idx,
        )
    )
    kinds = {c.source_kind for c in manifest.contributions}
    assert "immediate_user_turn_context" in kinds
    assert "committed_move" in kinds


def test_player_skip_suppresses_immediate_user_turn() -> None:
    kernel = DomainKernel.for_fixture_store()
    created = kernel.create_session(cast=["Alice"])
    scene_id = created.hg_scene_id
    kernel.record_user_turn(
        UserTurnRecordRequest.from_content(
            hg_session_id=scene_id,
            content="Look at the door number.",
            speaker="Player",
        )
    )
    kernel.record_player_skip(
        PlayerSkipRecordRequest(hg_session_id=scene_id, speaker="Player")
    )
    fixture = kernel.store.require(scene_id)
    assert project_immediate_user_turn_context(fixture.rp_history) is None


def test_occurrence_triggering_user_unchanged_when_promoted() -> None:
    fixture = initialize_live_session(cast=["Alice"], location="Workshop")
    fixture.rp_history.append(
        {
            "entry_id": "hist-u-promoted",
            "sequence_index": 0,
            "kind": "user",
            "content": "I look around the room.",
            "actor_id": "Player",
        }
    )
    commit_id = "commit-promoted-71"
    fixture.manager.public_events.append(
        PublicEvent(
            event_id="evt-71",
            timestamp=datetime.now(timezone.utc),
            event_type="action",
            participants=["Alice"],
            summary="Alice looks around.",
            turn_index=1,
            known_by=["Alice"],
            occurrence_evidence=OccurrenceEvidence(
                contributions=(),
                triggering_user=TriggeringUser(
                    entry_id="hist-u-promoted",
                    speaker="Player",
                    content="I look around the room.",
                ),
            ),
        )
    )
    turn = CharacterTurnRecord(
        character_id="Alice",
        committed_move=PROTOTYPE_VALID_MOVE,
        domain_commit_id=commit_id,
        continuity_turn_index=1,
        director_decision={},
    )
    trigger = extract_triggering_user_context(fixture, turn)
    assert trigger is not None
    assert trigger["entry_id"] == "hist-u-promoted"
    immediate = project_immediate_user_turn_context(fixture.rp_history)
    assert immediate is not None
    assert immediate["entry_id"] == "hist-u-promoted"


def test_dual_input_manifest_coexistence() -> None:
    kernel = DomainKernel.for_fixture_store()
    scene_id, round_id, commit_id, turn_idx = _commit_after_user(
        kernel,
        user_content="I look around the room.",
    )
    fixture = kernel.store.require(scene_id)
    user_entry_id = next(
        e["entry_id"] for e in fixture.rp_history if e.get("kind") == "user"
    )
    fixture.manager.public_events.append(
        PublicEvent(
            event_id="evt-dual-71",
            timestamp=datetime.now(timezone.utc),
            event_type="action",
            participants=["Alice"],
            summary="Alice looks around.",
            turn_index=turn_idx,
            known_by=["Alice"],
            occurrence_evidence=OccurrenceEvidence(
                contributions=(),
                triggering_user=TriggeringUser(
                    entry_id=user_entry_id,
                    speaker="Player",
                    content="I look around the room.",
                ),
            ),
        )
    )
    manifest = kernel.prepare_narrator_context(
        NarratorContextPrepareRequest(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-71-dual",
            character_id="Alice",
            domain_commit_id=commit_id,
            continuity_turn_index=turn_idx,
        )
    )
    kinds = [c.source_kind for c in manifest.contributions]
    assert "immediate_user_turn_context" in kinds
    assert "triggering_user_context" in kinds
    immediate = next(c for c in manifest.contributions if c.source_kind == "immediate_user_turn_context")
    occurrence = next(c for c in manifest.contributions if c.source_kind == "triggering_user_context")
    assert immediate.authority_class == "derived"
    assert occurrence.authority_class == "authoritative"
    occ_body = json.loads(occurrence.content)
    assert occ_body["triggering_user"] is not None
