"""Issue #144 — canonical Storyteller orientation response contract."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain.bootstrap import ensure_domain_paths

ensure_domain_paths()

from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.storyteller_contract import (  # noqa: E402
    PROHIBITED_STORYTELLER_FIELDS,
    STORYTELLER_ORIENTATION_SCHEMA,
    parse_storyteller_orientation,
)
from storyteller_orientation_response_contract import (  # noqa: E402
    BREADTH_VALUES,
    CANONICAL_EXEMPLAR,
    ORIENTATION_TRIGGER_VALUES,
    RESPONSE_CONTRACT_REVISION,
    STORYTELLER_ORIENTATION_SCHEMA as CONTRACT_SCHEMA,
    TEMPORAL_VALUES,
    project_storyteller_orientation_response_contract_text,
    response_contract_digest,
    storyteller_orientation_response_contract_provenance,
)


class Issue144StorytellerOrientationResponseContractTests(unittest.TestCase):
    def test_schema_has_single_canonical_authority(self) -> None:
        self.assertEqual(CONTRACT_SCHEMA, STORYTELLER_ORIENTATION_SCHEMA)
        self.assertEqual(CONTRACT_SCHEMA, "hg_storyteller_orientation_v1")

    def test_enum_authority_is_single_source(self) -> None:
        self.assertEqual(ORIENTATION_TRIGGER_VALUES, frozenset({"round_start", "material_commit_refresh", "follow_up_gap"}))
        self.assertEqual(TEMPORAL_VALUES, frozenset({"current", "recent", "historical", "session", "arc"}))
        self.assertEqual(BREADTH_VALUES, frozenset({"broad", "focused"}))

    def test_required_contract_fields_match_parser_requirements(self) -> None:
        text = project_storyteller_orientation_response_contract_text()
        self.assertIn(STORYTELLER_ORIENTATION_SCHEMA, text)
        self.assertIn("information_gaps", text)
        self.assertIn("schema", text.lower())

    def test_canonical_exemplar_parses(self) -> None:
        orientation, err = parse_storyteller_orientation(dict(CANONICAL_EXEMPLAR))
        self.assertIsNone(err)
        self.assertIsNotNone(orientation)
        self.assertEqual(len(orientation.information_gaps), 2)

    def test_optional_field_omission_still_succeeds_with_defaults(self) -> None:
        minimal = {
            "schema": STORYTELLER_ORIENTATION_SCHEMA,
            "information_gaps": ["What is the scene tension?"],
        }
        orientation, err = parse_storyteller_orientation(minimal)
        self.assertIsNone(err)
        self.assertIsNotNone(orientation)
        self.assertEqual(orientation.trigger, "round_start")
        self.assertEqual(orientation.temporal_focus, "current")
        self.assertEqual(orientation.breadth_preference, "broad")

    def test_missing_schema_is_schema_mismatch(self) -> None:
        orientation, err = parse_storyteller_orientation(
            {"information_gaps": ["What is happening?"]}
        )
        self.assertIsNone(orientation)
        self.assertEqual(err, "schema_mismatch")

    def test_empty_information_gaps_rejected(self) -> None:
        orientation, err = parse_storyteller_orientation(
            {"schema": STORYTELLER_ORIENTATION_SCHEMA, "information_gaps": []}
        )
        self.assertIsNone(orientation)
        self.assertEqual(err, "information_gaps_required")

    def test_prohibited_fields_rejected(self) -> None:
        payload = dict(CANONICAL_EXEMPLAR)
        payload["dialogue"] = "forbidden"
        orientation, err = parse_storyteller_orientation(payload)
        self.assertIsNone(orientation)
        self.assertTrue(err and err.startswith("prohibited_fields:"))

    def test_provenance_digest_is_stable(self) -> None:
        first = storyteller_orientation_response_contract_provenance()
        second = storyteller_orientation_response_contract_provenance()
        self.assertEqual(first["response_contract_revision"], RESPONSE_CONTRACT_REVISION)
        self.assertEqual(first, second)
        self.assertEqual(len(first["response_contract_digest"]), 64)
        self.assertEqual(first["response_contract_digest"], response_contract_digest())

    def test_projected_text_includes_exemplar_not_optional_fields(self) -> None:
        text = project_storyteller_orientation_response_contract_text()
        self.assertIn('"schema": "hg_storyteller_orientation_v1"', text)
        self.assertIn("What tensions are active in the scene?", text)
        self.assertNotIn("trigger", text)
        self.assertNotIn("temporal_focus", text)
        self.assertNotIn("breadth_preference", text)
        for field in ("next_actor", "dialogue", "narration", "structured_move"):
            self.assertIn(field, text)

    def test_prepare_includes_structural_and_behavioral_contributions(self) -> None:
        from domain_api.contract import RoundStartRequest

        kernel = DomainKernel.for_fixture_store()
        scene_id = kernel.create_scene().hg_scene_id
        round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
        prepared = kernel.prepare_storyteller_orientation_context(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-storyteller-144",
        )
        contributions = prepared["contributions"]
        instructions = [c for c in contributions if c["source_kind"] == "inference_instruction"]
        self.assertEqual(len(instructions), 2)
        structural = next(
            c for c in instructions if c["contribution_id"].endswith("storyteller_orientation_response_contract")
        )
        behavioral = next(
            c for c in instructions if c["contribution_id"].endswith("storyteller_orientation_instruction")
        )
        self.assertLess(structural["priority"], behavioral["priority"])
        self.assertEqual(structural["priority"], 28)
        self.assertEqual(behavioral["priority"], 100)
        self.assertIn("response_contract_revision", structural["provenance"])
        self.assertIn("response_contract_digest", structural["provenance"])
        self.assertNotIn("response_contract_digest", behavioral["provenance"])
        self.assertIn(STORYTELLER_ORIENTATION_SCHEMA, structural["content"])
        self.assertNotIn("Canonical exemplar", behavioral["content"])
        self.assertNotIn('"schema":', behavioral["content"])
        self.assertIn("STORYTELLER ORIENTATION TASK", behavioral["content"])

    def test_prohibited_fields_remain_shared_with_assessment(self) -> None:
        self.assertIn("dialogue", PROHIBITED_STORYTELLER_FIELDS)
        self.assertIn("next_actor", PROHIBITED_STORYTELLER_FIELDS)


if __name__ == "__main__":
    unittest.main()
