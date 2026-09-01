"""Issue #90 — auditability and legacy normalization tests."""

from __future__ import annotations

import unittest

from perceptual_visibility_contract import LEGACY_METADATA_KEY, METADATA_KEY
from perceptual_visibility_legacy import perceptual_visibility_record_from_entry_metadata
from perceptual_visibility_projection import (
    PERCEPTUAL_PROJECTOR_ID,
    PERCEPTUAL_PROJECTOR_VERSION,
    assemble_perceptual_history_entry_for_viewer,
    assemble_perceptual_visibility_for_viewer,
    build_perceptual_visibility_audit_metadata,
)
from perceptual_visibility_validation import (
    ValidationProfile,
    validate_perceptual_visibility_record,
)


class Issue90AuditabilityTests(unittest.TestCase):
    def test_valid_narrator_projection_audit_complete(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {
                    "type": "speech",
                    "dialogue": "Hello Bob",
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
                    "text": '"Hello Bob"',
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
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            source_entry_id="entry-1",
        )
        audit = build_perceptual_visibility_audit_metadata(assembly, record=record)[
            "perceptual_visibility_projection"
        ]
        self.assertEqual(audit["projector_id"], PERCEPTUAL_PROJECTOR_ID)
        self.assertEqual(audit["projector_version"], PERCEPTUAL_PROJECTOR_VERSION)
        self.assertEqual(audit["source_kind"], "narrator")
        self.assertEqual(audit["validation_status"], "valid")
        self.assertIn("u1", audit["included_unit_ids"])

    def test_legacy_metadata_normalization_flag(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [
                {
                    "type": "speech",
                    "dialogue": "Hello Bob",
                    "audibility": "directed",
                    "audience": ["Bob"],
                }
            ],
        }
        metadata = {
            LEGACY_METADATA_KEY: {
                "schema_version": 1,
                "record_id": "legacy-1",
                "units": [
                    {
                        "unit_id": "u1",
                        "kind": "speech",
                        "text": '"Hello Bob"',
                        "recipients": {"scope": "public"},
                        "beat_index": 0,
                    }
                ],
                "validation_status": "valid",
            }
        }
        record, prov = perceptual_visibility_record_from_entry_metadata(
            metadata,
            structured_move=move,
            acting_character="Alice",
        )
        assert record is not None
        self.assertTrue(prov["historical_normalization"])
        self.assertEqual(prov["legacy_metadata_key"], LEGACY_METADATA_KEY)
        self.assertIsNotNone(record.units[0].authority)
        assembly = assemble_perceptual_history_entry_for_viewer(
            {
                "entry_id": "e1",
                "kind": "presentation",
                "metadata": metadata,
            },
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            structured_move=move,
            acting_character="Alice",
            source_kind="narrator",
        )
        self.assertTrue(assembly.historical_normalization)
        self.assertNotIn(METADATA_KEY, metadata)

    def test_degraded_recovery_same_projector_and_no_poison(self) -> None:
        move = {
            "move_schema_version": 2,
            "beats": [{"type": "action", "action": "canonical action only"}],
        }
        assembly = assemble_perceptual_history_entry_for_viewer(
            {
                "entry_id": "e2",
                "kind": "presentation",
                "metadata": {},
            },
            viewer_character="Bob",
            present_characters=["Alice", "Bob"],
            structured_move=move,
            acting_character="Alice",
            source_kind="narrator",
        )
        self.assertEqual(assembly.degraded_path, "invalid_fallback_structured")
        self.assertEqual(assembly.projector_id, PERCEPTUAL_PROJECTOR_ID)
        self.assertNotIn("REJECTED", assembly.content or "")


if __name__ == "__main__":
    unittest.main()
