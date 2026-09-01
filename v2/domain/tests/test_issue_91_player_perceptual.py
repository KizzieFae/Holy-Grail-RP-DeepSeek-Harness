"""Issue #91 — player perceptual decomposition architecture tests."""

from __future__ import annotations

import unittest

from perceptual_visibility_contract import (
    METADATA_KEY,
    PLAYER_PERCEPT_UNAVAILABLE_MARKER,
    PLAYER_SOURCE_KIND,
)
from perceptual_visibility_projection import (
    assemble_perceptual_history_entry_for_viewer,
    build_perceptual_visibility_audit_metadata,
)
from player_decomposition_fixtures import (
    ISSUE_88_COMPLETION_TOKEN,
    ISSUE_88_DEPARTURE_TOKEN,
    ISSUE_88_PRIVATE_METHOD_TOKEN,
    ISSUE_88_RETURN_TOKEN,
    ISSUE_88_UNIT_COMPLETION,
    ISSUE_88_UNIT_DEPARTURE,
    ISSUE_88_UNIT_PRIVATE,
    ISSUE_88_UNIT_RETURN,
    build_issue_88_mixed_turn_fixture,
    build_multi_segment_player_decomposition,
    build_player_decomposition_for_content,
)
from player_perceptual_service import (
    FAILURE_MISSING_DECOMPOSITION,
    FAILURE_SOURCE_ACCOUNTING_INCOMPLETE,
    FAILURE_VALIDATION_REJECTED,
    validate_player_perceptual_decomposition,
)
from player_source_accounting import normalize_source_for_indexing


class Issue91PlayerPerceptualTests(unittest.TestCase):
    def test_complete_source_accounting_accepted(self) -> None:
        content = "Hello everyone."
        decomposition = build_player_decomposition_for_content(content)
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        self.assertEqual(record.source_kind, PLAYER_SOURCE_KIND)
        self.assertEqual(record.validation_status, "valid")

    def test_accounting_gap_rejected(self) -> None:
        content = "Hello."
        normalized = normalize_source_for_indexing(content)
        decomposition = build_player_decomposition_for_content(content)
        segments = decomposition["source_accounting"]["segments"]
        segments[0]["char_end"] = len(normalized) - 1
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertFalse(audit["accepted"])
        self.assertEqual(audit["failure_class"], FAILURE_SOURCE_ACCOUNTING_INCOMPLETE)

    def test_overlap_rejected(self) -> None:
        content = "AB"
        normalized = normalize_source_for_indexing(content)
        decomposition = {
            "perceptual_visibility": {
                "units": [
                    {
                        "unit_id": "u1",
                        "kind": "speech",
                        "text": normalized[0:1],
                        "recipients": {"scope": "public"},
                        "source_provenance": {"segment_ids": ["s1"], "order_index": 0},
                    },
                    {
                        "unit_id": "u2",
                        "kind": "speech",
                        "text": normalized[1:2],
                        "recipients": {"scope": "public"},
                        "source_provenance": {"segment_ids": ["s2"], "order_index": 1},
                    },
                ]
            },
            "source_accounting": {
                "segments": [
                    {
                        "segment_id": "s1",
                        "char_start": 0,
                        "char_end": 2,
                        "disposition": "projects",
                        "unit_ids": ["u1"],
                    },
                    {
                        "segment_id": "s2",
                        "char_start": 1,
                        "char_end": 2,
                        "disposition": "projects",
                        "unit_ids": ["u2"],
                    },
                ]
            },
        }
        _, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertFalse(audit["accepted"])

    def test_hidden_physical_event_vs_internal(self) -> None:
        content = "She slips the note into her pocket while thinking about escape."
        decomposition = build_multi_segment_player_decomposition(
            content,
            [
                {
                    "char_start": 0,
                    "char_end": 40,
                    "kind": "observable_event",
                    "scope": "private",
                    "characters": ["Alice"],
                },
                {
                    "char_start": 40,
                    "char_end": len(normalize_source_for_indexing(content)),
                    "kind": "internal",
                    "scope": "private",
                    "characters": ["Alice"],
                },
            ],
        )
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        kinds = {unit.kind for unit in record.units}
        self.assertIn("observable_event", kinds)
        self.assertIn("internal", kinds)

    def test_factual_claim_speech_not_rejected(self) -> None:
        content = "The door is unlocked."
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=build_player_decomposition_for_content(content, kind="speech"),
        )
        self.assertTrue(audit["accepted"])
        self.assertEqual(record.units[0].kind, "speech")

    def test_directed_speech_recipients(self) -> None:
        content = "Meet me at midnight."
        decomposition = build_player_decomposition_for_content(
            content,
            scope="directed",
            characters=["Bob"],
        )
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        entry = {
            "entry_id": "e1",
            "content": content,
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        bob = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        carol = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Carol",
            present_characters=["Alice", "Bob", "Carol"],
            source_kind="player",
        )
        self.assertIn("midnight", bob.content or "")
        self.assertIsNone(carol.content)

    def test_missing_decomposition_failure(self) -> None:
        record, audit = validate_player_perceptual_decomposition(
            content="Hello",
            speaker="Player",
            decomposition=None,
        )
        self.assertFalse(audit["accepted"])
        self.assertEqual(audit["failure_class"], FAILURE_MISSING_DECOMPOSITION)

    def test_current_failure_neutral_marker(self) -> None:
        record, _ = validate_player_perceptual_decomposition(
            content="Hello",
            speaker="Player",
            decomposition={"failure_class": "inference_unavailable", "reason": "down"},
        )
        entry = {
            "entry_id": "e-fail",
            "content": "Hello",
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        assembly = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice"],
            source_kind="player",
        )
        self.assertEqual(assembly.content, PLAYER_PERCEPT_UNAVAILABLE_MARKER)
        self.assertEqual(assembly.degraded_path, "decomposition_failed")

    def test_historical_missing_distinct_from_current_failure(self) -> None:
        entry = {"entry_id": "e-hist", "content": "Legacy line", "metadata": {}}
        assembly = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Alice",
            present_characters=["Alice"],
            source_kind="player",
        )
        self.assertIsNone(assembly.content)
        self.assertEqual(assembly.degraded_path, "historical_missing_player_decomposition")

    def test_projection_audit_metadata(self) -> None:
        content = "Hello Bob."
        decomposition = build_player_decomposition_for_content(content)
        record, _ = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        entry = {
            "entry_id": "e-audit",
            "content": content,
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        assembly = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            source_kind="player",
        )
        audit = build_perceptual_visibility_audit_metadata(assembly, record=record)[
            "perceptual_visibility_projection"
        ]
        self.assertEqual(audit["source_kind"], PLAYER_SOURCE_KIND)
        self.assertIn("u1", audit["included_unit_ids"])

    def test_presentation_only_rejected(self) -> None:
        content = "Hello."
        decomposition = build_player_decomposition_for_content(content, kind="presentation_only")
        _, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertFalse(audit["accepted"])
        self.assertEqual(audit["failure_class"], FAILURE_VALIDATION_REJECTED)


class Issue88MixedTurnRegressionTests(unittest.TestCase):
    """Parent Issue #88 seq-31/turn-12 mixed-visibility player-turn regression (#91)."""

    @classmethod
    def setUpClass(cls) -> None:
        import sys
        from pathlib import Path

        v2_root = Path(__file__).resolve().parents[2]
        if str(v2_root) not in sys.path:
            sys.path.insert(0, str(v2_root))
        from domain.bootstrap import ensure_domain_paths

        ensure_domain_paths()

    def test_issue_88_mixed_turn_harley_receives_completion_not_private_method(self) -> None:
        """#88 regression: unit-level projection must not whole-blob redact mixed player turns."""
        import json
        from pathlib import Path

        from domain_api.character_conversation_projection import (
            project_character_conversation_for_manifest,
            project_director_trigger_for_manifest,
        )
        from domain_api.contract import RoundStartRequest, UserTurnRecordRequest
        from domain_api.director_context_digests import project_user_turn_source_and_hints
        from domain_api.kernel import DomainKernel
        from perceptual_visibility_contract import METADATA_KEY, VALIDATION_AUDIT_KEY
        from perceptual_visibility_projection import (
            PERCEPTUAL_PROJECTOR_ID,
            PERCEPTUAL_PROJECTOR_VERSION,
            assemble_perceptual_history_entry_for_viewer,
            build_perceptual_visibility_audit_metadata,
        )
        from player_perceptual_service import validate_player_perceptual_decomposition

        content, decomposition = build_issue_88_mixed_turn_fixture()
        kernel = DomainKernel.for_fixture_store()
        created = kernel.create_session(cast=["Harley", "Celina", "Ayame"])
        scene_id = created.hg_scene_id
        round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
        entry = kernel.record_user_turn(
            UserTurnRecordRequest.from_content(
                hg_session_id=scene_id,
                content=content,
                speaker="Traveler",
                hg_round_id=round_id,
                player_decomposition=decomposition,
            )
        )
        fixture = kernel.store.require(scene_id)

        self.assertEqual(entry["content"], content)

        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        validation_audit = metadata.get(VALIDATION_AUDIT_KEY, {})
        self.assertTrue(validation_audit.get("accepted"))

        record, validation_result = validate_player_perceptual_decomposition(
            content=content,
            speaker="Traveler",
            decomposition=decomposition,
        )
        self.assertTrue(validation_result["accepted"])
        pvr = metadata.get(METADATA_KEY, {})
        unit_ids = {unit["unit_id"] for unit in pvr.get("units", [])}
        self.assertEqual(
            unit_ids,
            {
                ISSUE_88_UNIT_DEPARTURE,
                ISSUE_88_UNIT_PRIVATE,
                ISSUE_88_UNIT_RETURN,
                ISSUE_88_UNIT_COMPLETION,
            },
        )
        accounting = pvr.get("generation", {}).get("source_accounting", {})
        self.assertEqual(
            accounting.get("source_length"),
            len(normalize_source_for_indexing(content)),
        )
        self.assertTrue(accounting.get("segments"))

        assembly = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Harley",
            present_characters=["Harley", "Celina", "Ayame"],
            source_kind="player",
        )
        self.assertIsNotNone(assembly.content)
        harley_text = str(assembly.content)
        self.assertIn(ISSUE_88_DEPARTURE_TOKEN, harley_text)
        self.assertIn(ISSUE_88_RETURN_TOKEN, harley_text)
        self.assertIn(ISSUE_88_COMPLETION_TOKEN, harley_text)
        self.assertNotIn(ISSUE_88_PRIVATE_METHOD_TOKEN, harley_text)
        self.assertIn(ISSUE_88_UNIT_DEPARTURE, assembly.included_unit_ids)
        self.assertIn(ISSUE_88_UNIT_RETURN, assembly.included_unit_ids)
        self.assertIn(ISSUE_88_UNIT_COMPLETION, assembly.included_unit_ids)
        self.assertIn(ISSUE_88_UNIT_PRIVATE, assembly.excluded_unit_ids)
        self.assertEqual(
            assembly.exclusion_reasons.get(ISSUE_88_UNIT_PRIVATE),
            "recipient_ineligible",
        )

        projection_audit = build_perceptual_visibility_audit_metadata(assembly, record=record)[
            "perceptual_visibility_projection"
        ]
        self.assertEqual(projection_audit["projector_id"], PERCEPTUAL_PROJECTOR_ID)
        self.assertEqual(projection_audit["projector_version"], PERCEPTUAL_PROJECTOR_VERSION)
        self.assertIn(ISSUE_88_UNIT_PRIVATE, projection_audit["excluded_unit_ids"])

        transcript_content, trigger_content, provenance = project_character_conversation_for_manifest(
            fixture,
            character_id="Harley",
        )
        self.assertIsNotNone(transcript_content)
        self.assertIsNotNone(trigger_content)
        transcript_payload = json.loads(
            transcript_content.split(":\n", 1)[1]
            if ":\n" in transcript_content
            else transcript_content
        )
        self.assertTrue(transcript_payload)
        combined_transcript = json.dumps(transcript_payload)
        self.assertIn(ISSUE_88_COMPLETION_TOKEN, combined_transcript)
        self.assertNotIn(ISSUE_88_PRIVATE_METHOD_TOKEN, combined_transcript)
        self.assertIn(ISSUE_88_DEPARTURE_TOKEN, combined_transcript)

        self.assertIn(ISSUE_88_COMPLETION_TOKEN, trigger_content or "")
        self.assertNotIn(ISSUE_88_PRIVATE_METHOD_TOKEN, trigger_content or "")
        self.assertIn("perceptual_visibility_projection", provenance)

        director_trigger, director_prov = project_director_trigger_for_manifest(fixture)
        self.assertIsNotNone(director_trigger)
        self.assertIn(content, director_trigger or "")
        self.assertFalse(director_prov.get("trigger_redacted"))

        director_contribs, _ = project_user_turn_source_and_hints(
            fixture,
            eligible=["Harley", "Celina", "Ayame"],
            manifest_id="manifest-issue-88-regression",
        )
        director_source = next(
            c for c in director_contribs if c.source_kind == "user_turn_source"
        )
        self.assertIn(content, director_source.content)
        self.assertFalse(director_source.provenance.get("trigger_redacted"))

        legacy_module = (
            Path(__file__).resolve().parents[1] / "modules" / "perception_audibility_player.py"
        )
        self.assertFalse(legacy_module.exists())
        import perception_audibility as audibility

        self.assertNotIn("player_text_for_character_viewer", audibility.__all__)


if __name__ == "__main__":
    unittest.main()
