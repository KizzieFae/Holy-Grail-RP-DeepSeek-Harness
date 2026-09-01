"""Issue #92 — Character perceptual projection architecture tests."""

from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

_V2 = Path(__file__).resolve().parents[2]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from character_move_ingress import ingest_character_move_json_object  # noqa: E402
from character_perceptual_service import (  # noqa: E402
    CHARACTER_DERIVATION_PROFILE,
    CHARACTER_SOURCE_KIND,
    HISTORICAL_PARTIAL_FAILURE_CLASS,
    build_historical_partial_character_record,
    derive_character_perceptual_record,
)
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    ContextPrepareRequest,
    RoundStartRequest,
    ValidationRequest,
)
from domain_api.kernel import DomainKernel, PROTOTYPE_DIRECTOR_DECISION  # noqa: E402
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_history import (  # noqa: E402
    history_entries,
    project_history_to_character_context_chat,
)
from memory_layer.writes import resolve_present_characters  # noqa: E402
from perceptual_visibility_contract import METADATA_KEY  # noqa: E402
from perceptual_visibility_projection import (  # noqa: E402
    PERCEPTUAL_PROJECTOR_ID,
    assemble_perceptual_history_entry_for_viewer,
    build_perceptual_visibility_audit_metadata,
)


PUBLIC_ACTION = "PUBLIC_ACTION_TOKEN_92"
PRIVATE_ACTION = "PRIVATE_ACTION_TOKEN_92"
PUBLIC_AFTER = "PUBLIC_AFTER_TOKEN_92"
PUBLIC_SPEECH = "PUBLIC_SPEECH_TOKEN_92"
DIRECTED_SPEECH = "DIRECTED_SPEECH_TOKEN_92"


def _motivation() -> dict[str, str]:
    return {
        "goal": "advance scene",
        "tactic": "mixed visibility beat",
        "emotional_driver": "focused",
        "risk_level": "medium",
    }


def build_issue_92_mixed_move() -> dict:
    return {
        "move_schema_version": 2,
        "beats": [
            {"type": "action", "action": PUBLIC_ACTION},
            {
                "type": "action",
                "action": PRIVATE_ACTION,
                "recipients": {"scope": "private", "characters": ["Alice"]},
            },
            {"type": "action", "action": PUBLIC_AFTER},
            {"type": "speech", "dialogue": PUBLIC_SPEECH, "audibility": "public"},
            {
                "type": "speech",
                "dialogue": DIRECTED_SPEECH,
                "audibility": "directed",
                "audience": ["Bob"],
            },
        ],
        "motivation": _motivation(),
        "semantic_evaluation": {"decision": "no_covered_change"},
    }


class Issue92CharacterPerceptualTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        repository = SessionRepository(Path(self._tmpdir.name) / "sessions")
        self.kernel = DomainKernel.for_repository(repository)
        info = self.kernel.create_session(cast=["Alice", "Bob", "Carol"])
        self.hg_scene_id = info.hg_scene_id
        self.hg_round_id = self.kernel.start_round(
            RoundStartRequest(hg_scene_id=self.hg_scene_id)
        ).hg_round_id
        self.fixture = self.kernel.store.require(self.hg_scene_id)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _validate_and_commit(self, *, character_id: str, move: dict) -> str:
        validation = self.kernel.validate_move(
            ValidationRequest(
                inference_id=f"inf-{character_id}-92",
                hg_scene_id=self.hg_scene_id,
                hg_round_id=self.hg_round_id,
                character_id=character_id,
                role="guest",
                turn_index=0,
                attempt_index=0,
                proposed_move=move,
                raw_model_output=json.dumps(move),
            )
        )
        self.assertTrue(validation.accepted, validation.reason)
        self.assertIsNotNone(validation.perceptual_visibility)
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id=f"inf-{character_id}-92",
                hg_scene_id=self.hg_scene_id,
                hg_round_id=self.hg_round_id,
                character_id=character_id,
                validated_move=dict(validation.normalized_move or {}),
                director_decision=dict(PROTOTYPE_DIRECTOR_DECISION),
                expected_turn_index=0,
            )
        )
        self.assertTrue(commit.committed, commit.reason)
        assert commit.domain_commit_id is not None
        return commit.domain_commit_id

    def _projected_content(self, *, viewer: str) -> str:
        present = resolve_present_characters(
            continuity_manager=self.fixture.manager,
            char_names=list(self.fixture.cast),
        )
        chat = project_history_to_character_context_chat(
            self.fixture.rp_history,
            character_id=viewer,
            character_names=list(self.fixture.cast),
            present_characters=present,
            get_character_display_name_fn=lambda name: name,
        )
        return "\n".join(str(item.get("content", "")) for item in chat)

    def test_action_recipients_ingress_defaults_and_validation(self) -> None:
        move, err = ingest_character_move_json_object(
            {
                "move_schema_version": 2,
                "beats": [{"type": "action", "action": "waves"}],
                "motivation": _motivation(),
                "semantic_evaluation": {"decision": "no_covered_change"},
            }
        )
        self.assertEqual(err, "")
        assert move is not None
        derivation = derive_character_perceptual_record(move, acting_character="Alice")
        self.assertTrue(derivation.accepted)
        assert derivation.record is not None
        action_unit = next(
            unit for unit in derivation.record.units if unit.kind == "observable_event"
        )
        self.assertEqual(action_unit.recipients.get("scope"), "present")

        bad, bad_err = ingest_character_move_json_object(
            {
                "move_schema_version": 2,
                "beats": [
                    {
                        "type": "action",
                        "action": "whispers secretly",
                        "recipients": {"scope": "private", "characters": []},
                    }
                ],
                "motivation": _motivation(),
                "semantic_evaluation": {"decision": "no_covered_change"},
            }
        )
        self.assertIsNone(bad)
        self.assertIn("private action requires", bad_err)

    def test_mandatory_mixed_action_regression(self) -> None:
        move = build_issue_92_mixed_move()
        commit_id = self._validate_and_commit(character_id="Alice", move=move)

        committed = next(
            entry
            for entry in history_entries(self.fixture.rp_history)
            if entry.kind == "committed_turn" and entry.domain_commit_id == commit_id
        )
        metadata = committed.metadata or {}
        director_move = metadata.get("structured_move")
        self.assertIsInstance(director_move, dict)
        self.assertEqual(len(director_move.get("beats", [])), 5)

        pvr_raw = metadata.get(METADATA_KEY)
        self.assertIsInstance(pvr_raw, dict)
        self.assertEqual(pvr_raw.get("source_kind"), CHARACTER_SOURCE_KIND)
        self.assertEqual(pvr_raw.get("validation_status"), "valid")
        units = pvr_raw.get("units") or []
        self.assertEqual(len(units), 5)
        for unit in units:
            provenance = unit.get("source_provenance") or {}
            self.assertIn("beat_index", provenance)
            self.assertEqual(provenance.get("derivation_profile"), CHARACTER_DERIVATION_PROFILE)

        carol_text = self._projected_content(viewer="Carol")
        bob_text = self._projected_content(viewer="Bob")
        alice_text = self._projected_content(viewer="Alice")

        self.assertIn(PUBLIC_ACTION, carol_text)
        self.assertIn(PUBLIC_AFTER, carol_text)
        self.assertIn(PUBLIC_SPEECH, carol_text)
        self.assertNotIn(PRIVATE_ACTION, carol_text)
        self.assertNotIn(DIRECTED_SPEECH, carol_text)

        self.assertIn(PUBLIC_ACTION, bob_text)
        self.assertIn(PUBLIC_AFTER, bob_text)
        self.assertIn(PUBLIC_SPEECH, bob_text)
        self.assertIn(DIRECTED_SPEECH, bob_text)
        self.assertNotIn(PRIVATE_ACTION, bob_text)

        self.assertIn(PRIVATE_ACTION, alice_text)
        self.assertIn(PUBLIC_ACTION, alice_text)
        self.assertIn(DIRECTED_SPEECH, alice_text)

        present = resolve_present_characters(
            continuity_manager=self.fixture.manager,
            char_names=list(self.fixture.cast),
        )
        assembly = assemble_perceptual_history_entry_for_viewer(
            committed.to_dict(),
            viewer_character="Carol",
            present_characters=present,
            structured_move=director_move,
            acting_character="Alice",
            source_kind="character",
        )
        audit = build_perceptual_visibility_audit_metadata(assembly)
        projection = audit.get("perceptual_visibility_projection") or {}
        self.assertEqual(projection.get("projector_id"), PERCEPTUAL_PROJECTOR_ID)
        self.assertTrue(projection.get("included_unit_ids"))
        self.assertTrue(projection.get("excluded_unit_ids"))

        carol_state = self.fixture.character_states["Carol"]
        carol_memory = "\n".join(carol_state.private_memories)
        self.assertIn(PUBLIC_ACTION, carol_memory)
        self.assertNotIn(PRIVATE_ACTION, carol_memory)
        self.assertNotIn(DIRECTED_SPEECH, carol_memory)

        alice_state = self.fixture.character_states["Alice"]
        alice_memory = "\n".join(alice_state.private_memories)
        self.assertIn(PRIVATE_ACTION, alice_memory)

        manifest = self.kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=self.hg_scene_id,
                hg_round_id=self.hg_round_id,
                inference_id="inf-bob-ctx-92",
                character_id="Bob",
                role="guest",
                turn_index=1,
                attempt_index=0,
            )
        )
        transcript = next(
            c for c in manifest.contributions if c.source_kind == "recent_scene_transcript"
        )
        self.assertIn(DIRECTED_SPEECH, transcript.content)
        self.assertNotIn(PRIVATE_ACTION, transcript.content)

    def test_historical_safe_partial_recovery(self) -> None:
        move = build_issue_92_mixed_move()
        entry = {
            "entry_id": "hist-92",
            "sequence_index": 0,
            "kind": "committed_turn",
            "content": "summary",
            "actor_id": "Alice",
            "metadata": {"structured_move": move},
        }
        record = build_historical_partial_character_record(move, acting_character="Alice")
        assert record is not None
        self.assertEqual(record.validation_status, "historical_partial")
        self.assertEqual(
            record.recovery.get("failure_class"),
            HISTORICAL_PARTIAL_FAILURE_CLASS,
        )

        carol = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Carol",
            present_characters=["Alice", "Bob", "Carol"],
            structured_move=move,
            acting_character="Alice",
            source_kind="character",
        )
        self.assertIn(PUBLIC_SPEECH, str(carol.content or ""))
        self.assertNotIn(PRIVATE_ACTION, str(carol.content or ""))

        alice = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice", "Bob", "Carol"],
            structured_move=move,
            acting_character="Alice",
            source_kind="character",
        )
        self.assertIn(PRIVATE_ACTION, str(alice.content or ""))

    def test_legacy_character_formatter_removed_from_session_history(self) -> None:
        module = importlib.import_module("domain_api.session_history")
        self.assertFalse(hasattr(module, "committed_observable_content_for_character"))
        source = Path(module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("format_observable_v2_turn_for_viewer", source)

    def test_validate_move_rejects_invalid_private_action_recipients(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {
                    "type": "action",
                    "action": "concealed gesture",
                    "recipients": {"scope": "private", "characters": []},
                }
            ],
            "motivation": _motivation(),
            "semantic_evaluation": {"decision": "no_covered_change"},
        }
        validation = self.kernel.validate_move(
            ValidationRequest(
                inference_id="inf-invalid-92",
                hg_scene_id=self.hg_scene_id,
                hg_round_id=self.hg_round_id,
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
                proposed_move=move,
                raw_model_output=json.dumps(move),
            )
        )
        self.assertFalse(validation.accepted)


if __name__ == "__main__":
    unittest.main()
