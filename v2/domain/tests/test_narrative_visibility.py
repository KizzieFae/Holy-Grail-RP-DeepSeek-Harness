"""Issue #81 — NarrativeVisibilityRecord validation and projection unit tests."""

from __future__ import annotations

import unittest

from narrative_visibility_validation import validate_narrative_visibility_record
from narrative_visibility_projection import assemble_narrative_visibility_for_viewer
from narrative_visibility_contract import NarrativeVisibilityRecord


class NarrativeVisibilityValidationTests(unittest.TestCase):
    def test_internal_cannot_be_public(self) -> None:
        result = validate_narrative_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "internal",
                    "text": "secret thought",
                    "recipients": {"scope": "public"},
                }
            ]
        )
        self.assertFalse(result.accepted)

    def test_speech_requires_beat_index_and_move(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {"type": "speech", "dialogue": "Hello Bob", "audibility": "directed", "audience": ["Bob"]}
            ],
        }
        result = validate_narrative_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "speech",
                    "text": '"Hello Bob"',
                    "recipients": {"scope": "public"},
                    "beat_index": 0,
                }
            ],
            structured_move=move,
            acting_character="Alice",
        )
        self.assertTrue(result.accepted)

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
        record = validate_narrative_visibility_record(
            units_raw=[
                {
                    "unit_id": "u1",
                    "kind": "speech",
                    "text": '"Secret for Bob only"',
                    "recipients": {"scope": "public"},
                    "beat_index": 0,
                }
            ],
            structured_move=move,
            acting_character="Alice",
        ).record
        assert record is not None
        assembly = assemble_narrative_visibility_for_viewer(
            record,
            viewer_character="Carol",
            present_characters=["Alice", "Bob", "Carol"],
            structured_move=move,
            acting_character="Alice",
        )
        self.assertIsNone(assembly.content)
        self.assertIn("u1", assembly.excluded_unit_ids)


class NarrativeVisibilityProjectionTests(unittest.TestCase):
    def test_mixed_units_assemble_rich_subset(self) -> None:
        record = NarrativeVisibilityRecord.from_dict(
            {
                "schema_version": 1,
                "record_id": "nvr-test",
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
        bob_view = assemble_narrative_visibility_for_viewer(
            record,
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
        )
        self.assertIn("Brown walls", bob_view.content or "")
        self.assertNotIn("wondered", bob_view.content or "")


if __name__ == "__main__":
    unittest.main()
