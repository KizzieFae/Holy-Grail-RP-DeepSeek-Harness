"""Issue #120 — generalized player internal semantic contract tests."""

from __future__ import annotations

import unittest

from perceptual_visibility_contract import METADATA_KEY
from perceptual_visibility_projection import assemble_perceptual_history_entry_for_viewer
from player_decomposition_fixtures import (
    ISSUE_120_JAPAN_TOKEN,
    ISSUE_120_UNIT_HESITATION,
    ISSUE_120_UNIT_JAPAN,
    ISSUE_120_UNIT_SEIZA,
    ISSUE_120_UNIT_SPEECH_1,
    ISSUE_120_UNIT_SPEECH_2,
    build_issue_120_seiza_japan_fixture,
    build_multi_segment_player_decomposition,
    build_player_decomposition_for_content,
)
from player_perceptual_service import validate_player_perceptual_decomposition
from player_source_accounting import normalize_source_for_indexing


class Issue120GeneralizedInternalTests(unittest.TestCase):
    def test_seiza_japan_fixture_validates_and_projects(self) -> None:
        content, decomposition = build_issue_120_seiza_japan_fixture()
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        kinds = {unit.kind for unit in record.units}
        self.assertIn("observable_event", kinds)
        self.assertIn("internal", kinds)
        self.assertIn("speech", kinds)

        japan_unit = next(unit for unit in record.units if unit.unit_id == ISSUE_120_UNIT_JAPAN)
        self.assertEqual(japan_unit.kind, "internal")
        self.assertIn(ISSUE_120_JAPAN_TOKEN, japan_unit.text)

        entry = {
            "entry_id": "e-seiza-japan",
            "content": content,
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        ayame = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=["Ayame", "Kizzie", "Harley", "Celina"],
            source_kind="player",
        )
        self.assertIn(ISSUE_120_UNIT_SEIZA, ayame.included_unit_ids)
        self.assertIn(ISSUE_120_UNIT_SPEECH_1, ayame.included_unit_ids)
        self.assertIn(ISSUE_120_UNIT_HESITATION, ayame.included_unit_ids)
        self.assertIn(ISSUE_120_UNIT_SPEECH_2, ayame.included_unit_ids)
        self.assertIn(ISSUE_120_UNIT_JAPAN, ayame.excluded_unit_ids)
        self.assertEqual(
            ayame.exclusion_reasons.get(ISSUE_120_UNIT_JAPAN),
            "player_internal_ineligible",
        )
        self.assertNotIn(ISSUE_120_JAPAN_TOKEN, ayame.content or "")

    def test_genuine_cognition_remains_internal(self) -> None:
        content = "Kizzie wondered whether Ayame believed her."
        decomposition = build_player_decomposition_for_content(
            content,
            kind="internal",
            scope="private",
            characters=["Kizzie"],
        )
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        entry = {
            "entry_id": "e-cognition",
            "content": content,
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        ayame = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=["Ayame", "Kizzie"],
            source_kind="player",
        )
        self.assertIsNone(ayame.content)
        self.assertEqual(ayame.exclusion_reasons.get("u1"), "player_internal_ineligible")

    def test_concealed_physical_event_not_internal(self) -> None:
        content = (
            "She slips the note into her pocket while thinking about escape."
        )
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
        self.assertNotEqual(kinds, {"internal"})

    def test_mixed_observable_and_nonperceptual_narration(self) -> None:
        action = "Kizzie settled into seiza."
        narration = " They weren't in Japan, but old habits died hard."
        content = action + narration
        normalized = normalize_source_for_indexing(content)
        action_end = len(normalize_source_for_indexing(action))
        decomposition = build_multi_segment_player_decomposition(
            content,
            [
                {
                    "char_start": 0,
                    "char_end": action_end,
                    "kind": "observable_event",
                    "scope": "present",
                },
                {
                    "char_start": action_end,
                    "char_end": len(normalized),
                    "kind": "internal",
                    "scope": "private",
                    "characters": ["Kizzie"],
                },
            ],
        )
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        entry = {
            "entry_id": "e-mixed",
            "content": content,
            "metadata": {METADATA_KEY: record.to_dict()},
        }
        ayame = assemble_perceptual_history_entry_for_viewer(
            entry,
            viewer_character="Ayame",
            present_characters=["Ayame", "Kizzie"],
            source_kind="player",
        )
        self.assertIn("seiza", ayame.content or "")
        self.assertNotIn("Japan", ayame.content or "")


if __name__ == "__main__":
    unittest.main()
