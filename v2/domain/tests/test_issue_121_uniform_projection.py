"""Issue #121 — uniform projection synthesis and checker-route tests."""

from __future__ import annotations

import unittest

from perceptual_visibility_contract import PLAYER_SOURCE_KIND
from perceptual_visibility_projection import (
    assemble_perceptual_history_entry_for_viewer,
    build_perceptual_visibility_audit_metadata,
)
from player_decomposition_fixtures import build_issue_120_seiza_japan_fixture
from player_perceptual_service import (
    FAILURE_VALIDATION_REJECTED,
    validate_player_perceptual_decomposition,
)
from player_uniform_projection import (
    UNIFORM_PROJECTION_KIND,
    build_uniform_projection_decomposition,
)
from player_visibility_triage_corpus import build_issue_121_checker_corpus


class Issue121UniformProjectionTests(unittest.TestCase):
    def test_uniform_synthesis_validates_and_projects(self) -> None:
        content = 'The player waves. "Good morning," they say.'
        decomposition = build_uniform_projection_decomposition(
            content,
            checker_audit={
                "uniform_projection_safe": True,
                "reason": "affirmative_uniform_present",
                "inference_id": "test-checker",
            },
        )
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        self.assertEqual(audit.get("route"), "uniform_projection")
        self.assertEqual(record.units[0].kind, UNIFORM_PROJECTION_KIND)
        self.assertEqual(record.units[0].recipients.get("scope"), "present")
        self.assertEqual(record.generation.get("semantic_decomposition"), "not_performed")

        entry = {
            "entry_id": "entry-uniform",
            "kind": "user",
            "content": content,
            "metadata": {"perceptual_visibility": record.to_dict()},
        }
        for viewer in ("Ayame", "Harley"):
            assembly = assemble_perceptual_history_entry_for_viewer(
                entry,
                viewer_character=viewer,
                present_characters=["Ayame", "Harley", "Kizzie"],
                source_kind=PLAYER_SOURCE_KIND,
            )
            self.assertEqual(assembly.content, content)
            self.assertIn("u_uniform", assembly.included_unit_ids)
            audit_meta = build_perceptual_visibility_audit_metadata(assembly, record=record)
            self.assertIn("u_uniform", audit_meta["perceptual_visibility_projection"]["included_unit_ids"])

    def test_semantic_path_rejects_uniform_projection_kind(self) -> None:
        content = "Hello."
        decomposition = build_uniform_projection_decomposition(
            content,
            checker_audit={"uniform_projection_safe": True, "reason": "affirmative_uniform_present"},
        )
        decomposition["generation"]["synthesis_route"] = "semantic_decomposition_forged"
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertFalse(audit["accepted"])
        self.assertEqual(audit["failure_class"], FAILURE_VALIDATION_REJECTED)

    def test_semantic_pvr_cannot_emit_uniform_projection_kind(self) -> None:
        content = "Hello."
        decomposition = {
            "perceptual_visibility": {
                "units": [
                    {
                        "unit_id": "u1",
                        "kind": UNIFORM_PROJECTION_KIND,
                        "text": content,
                        "recipients": {"scope": "present", "characters": [], "roles": []},
                        "source_provenance": {"segment_ids": ["s1"], "order_index": 0},
                        "source": "player_decomposition",
                    }
                ]
            },
            "source_accounting": {
                "segments": [
                    {
                        "segment_id": "s1",
                        "char_start": 0,
                        "char_end": len(content),
                        "disposition": "projects",
                        "unit_ids": ["u1"],
                    }
                ]
            },
            "generation": {"inference_id": "semantic-forged"},
        }
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Player",
            decomposition=decomposition,
        )
        self.assertFalse(audit["accepted"])
        self.assertIn("uniform_projection not permitted", audit["reason"])

    def test_seiza_japan_semantic_fixture_still_projects_with_internal(self) -> None:
        content, decomposition = build_issue_120_seiza_japan_fixture()
        record, audit = validate_player_perceptual_decomposition(
            content=content,
            speaker="Kizzie",
            decomposition=decomposition,
        )
        self.assertTrue(audit["accepted"])
        self.assertNotEqual(audit.get("route"), "uniform_projection")

    def test_checker_corpus_expectations_defined(self) -> None:
        corpus = build_issue_121_checker_corpus()
        self.assertGreaterEqual(len(corpus), 12)
        safety_critical = [case for case in corpus if case.safety_critical]
        self.assertTrue(any(case.case_id == "neg_seiza_japan_120" for case in safety_critical))
        self.assertTrue(any(case.case_id == "neg_issue_88_mixed" for case in safety_critical))
