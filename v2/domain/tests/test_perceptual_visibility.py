"""Issue #81 / #90 — PerceptualVisibilityRecord validation and projection unit tests."""

from __future__ import annotations

import unittest

from perceptual_visibility_projection import (
    PERCEPTUAL_PROJECTOR_ID,
    assemble_perceptual_visibility_for_viewer,
)
from perceptual_visibility_contract import PerceptualVisibilityRecord
from perceptual_visibility_validation import (
    ValidationProfile,
    build_degraded_perceptual_record_from_structured_move,
    validate_perceptual_visibility_record,
)


class PerceptualVisibilityValidationTests(unittest.TestCase):
    def test_internal_cannot_be_public(self) -> None:
        result = validate_perceptual_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "internal",
                    "text": "secret thought",
                    "recipients": {"scope": "public"},
                }
            ],
            profile=ValidationProfile.OPENING,
            source_kind="opening",
        )
        self.assertFalse(result.accepted)

    def test_speech_requires_beat_index_and_move(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {"type": "speech", "dialogue": "Hello Bob", "audibility": "directed", "audience": ["Bob"]}
            ],
        }
        result = validate_perceptual_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "speech",
                    "text": '"Hello Bob"',
                    "recipients": {"scope": "public"},
                    "beat_index": 0,
                }
            ],
            profile=ValidationProfile.NARRATOR_PRESENTATION,
            structured_move=move,
            acting_character="Alice",
            source_kind="narrator",
        )
        self.assertTrue(result.accepted)
        assert result.record is not None
        self.assertIsNotNone(result.record.units[0].authority)

    def test_opening_speech_without_beat_index_passes(self) -> None:
        result = validate_perceptual_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "speech",
                    "text": '"Welcome," she said.',
                    "recipients": {"scope": "public"},
                }
            ],
            profile=ValidationProfile.OPENING,
            source_kind="opening",
        )
        self.assertTrue(result.accepted)
        assert result.record is not None
        self.assertIsNone(result.record.units[0].source_provenance.get("beat_index"))

    def test_narrator_speech_without_beat_index_rejected(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {"type": "speech", "dialogue": "Hello Bob", "audibility": "directed", "audience": ["Bob"]}
            ],
        }
        result = validate_perceptual_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "speech",
                    "text": '"Hello Bob"',
                    "recipients": {"scope": "public"},
                }
            ],
            profile=ValidationProfile.NARRATOR_PRESENTATION,
            structured_move=move,
            acting_character="Alice",
            source_kind="narrator",
        )
        self.assertFalse(result.accepted)
        self.assertIn("missing beat_index", result.reason)

    def test_opening_instruction_aligns_with_opening_provenance(self) -> None:
        from narrative_visibility_prompt import OPENING_SEGMENTATION_OUTPUT_INSTRUCTION

        self.assertIn("Do NOT include beat_index", OPENING_SEGMENTATION_OUTPUT_INSTRUCTION)
        self.assertNotIn('"beat_index"', OPENING_SEGMENTATION_OUTPUT_INSTRUCTION)

    def test_structured_authority_narrows_speech(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {
                    "type": "speech",
                    "dialogue": "Secret for Bob only",
                    "audibility": "directed",
                    "audience": ["Bob"],
                }
            ],
        }
        record = validate_perceptual_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "speech",
                    "text": '"Secret for Bob only"',
                    "recipients": {"scope": "public"},
                    "beat_index": 0,
                }
            ],
            profile=ValidationProfile.NARRATOR_PRESENTATION,
            structured_move=move,
            acting_character="Alice",
            source_kind="narrator",
        ).record
        assert record is not None
        assembly = assemble_perceptual_visibility_for_viewer(
            record,
            viewer_character="Carol",
            present_characters=["Alice", "Bob", "Carol"],
        )
        self.assertIsNone(assembly.content)
        self.assertIn("u1", assembly.excluded_unit_ids)
        self.assertIn("u1", assembly.authority_narrowed_unit_ids)


class PerceptualVisibilityProjectionTests(unittest.TestCase):
    def test_mixed_units_assemble_rich_subset(self) -> None:
        record = PerceptualVisibilityRecord.from_dict(
            {
                "schema_version": 2,
                "record_id": "pvr-test",
                "source_kind": "opening",
                "units": [
                    {
                        "unit_id": "scene",
                        "kind": "observable_scene",
                        "text": "Brown walls and plush carpet lined the hall.",
                        "recipients": {"scope": "public"},
                    },
                    {
                        "unit_id": "internal",
                        "kind": "internal",
                        "text": "She wondered if anyone noticed her fear.",
                        "recipients": {"scope": "private", "characters": ["Alice"]},
                    },
                ],
            }
        )
        assert record is not None
        bob_view = assemble_perceptual_visibility_for_viewer(
            record,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
        )
        self.assertIn("Brown walls", bob_view.content or "")
        self.assertNotIn("wondered", bob_view.content or "")
        self.assertEqual(bob_view.projector_id, PERCEPTUAL_PROJECTOR_ID)

    def test_degraded_record_uses_structured_text_only(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {"type": "action", "action": "looked around"},
                {
                    "type": "speech",
                    "dialogue": "Canonical line",
                    "audibility": "public",
                },
            ],
        }
        record = build_degraded_perceptual_record_from_structured_move(
            move,
            acting_character="Alice",
            source_kind="narrator",
        )
        assert record is not None
        self.assertEqual(record.validation_status, "invalid_fallback_structured")
        poison = "REJECTED_NARRATOR_POISON"
        for unit in record.units:
            self.assertNotIn(poison, unit.text)
        assembly = assemble_perceptual_visibility_for_viewer(
            record,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
        )
        self.assertIn("Canonical line", assembly.content or "")
        self.assertEqual(assembly.degraded_path, "invalid_fallback_structured")


if __name__ == "__main__":
    unittest.main()
