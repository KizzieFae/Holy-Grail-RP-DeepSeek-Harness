"""Issue #146 — canonical Storyteller assessment response contract."""

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

from domain_api.contract import RoundStartRequest  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.storyteller_contract import (  # noqa: E402
    PROHIBITED_STORYTELLER_FIELDS,
    STORYTELLER_ASSESSMENT_SCHEMA,
    StorytellerAuditRecord,
    StorytellerBundleRefs,
    StorytellerOrientationAssessment,
    build_storyteller_advisory_package,
    parse_storyteller_assessment,
    parse_storyteller_orientation,
)
from storyteller_assessment_response_contract import (  # noqa: E402
    CANONICAL_EXEMPLAR,
    CANONICAL_SECTION_NAMES,
    RESPONSE_CONTRACT_REVISION,
    STORYTELLER_ASSESSMENT_SCHEMA as CONTRACT_SCHEMA,
    project_storyteller_assessment_response_contract_text,
    response_contract_digest,
    storyteller_assessment_response_contract_provenance,
)


def _orientation() -> StorytellerOrientationAssessment:
    parsed, _ = parse_storyteller_orientation(
        {
            "schema": "hg_storyteller_orientation_v1",
            "information_gaps": ["What tensions are active?"],
        }
    )
    assert parsed is not None
    return parsed


class Issue146StorytellerAssessmentResponseContractTests(unittest.TestCase):
    def test_schema_has_single_canonical_authority(self) -> None:
        self.assertEqual(CONTRACT_SCHEMA, STORYTELLER_ASSESSMENT_SCHEMA)
        self.assertEqual(CONTRACT_SCHEMA, "hg_storyteller_assessment_v1")

    def test_canonical_section_vocabulary_authority(self) -> None:
        self.assertIn("observations", CANONICAL_SECTION_NAMES)
        self.assertIn("progression_opportunities", CANONICAL_SECTION_NAMES)
        self.assertIn("evidence_refs", CANONICAL_SECTION_NAMES)

    def test_canonical_exemplar_parses(self) -> None:
        parsed, err = parse_storyteller_assessment(dict(CANONICAL_EXEMPLAR))
        self.assertIsNone(err)
        self.assertIsNotNone(parsed)

    def test_canonical_exemplar_builds_useful_package(self) -> None:
        parsed, _ = parse_storyteller_assessment(dict(CANONICAL_EXEMPLAR))
        assert parsed is not None
        package = build_storyteller_advisory_package(
            assessment=parsed,
            orientation=_orientation(),
            hg_scene_id="scene-1",
            bundle_refs=StorytellerBundleRefs(
                primary_request_id="req-1",
                primary_bundle_id="bundle-1",
            ),
            authoritative_snapshot_id="snap-1",
            audit=StorytellerAuditRecord(),
        )
        self.assertTrue(len(package.observations) > 0 or len(package.progression_opportunities) > 0)

    def test_schema_only_object_remains_parser_valid(self) -> None:
        parsed, err = parse_storyteller_assessment({"schema": STORYTELLER_ASSESSMENT_SCHEMA})
        self.assertIsNone(err)
        self.assertIsNotNone(parsed)

    def test_schema_only_package_is_operationally_empty(self) -> None:
        parsed, _ = parse_storyteller_assessment({"schema": STORYTELLER_ASSESSMENT_SCHEMA})
        assert parsed is not None
        package = build_storyteller_advisory_package(
            assessment=parsed,
            orientation=_orientation(),
            hg_scene_id="scene-1",
            bundle_refs=StorytellerBundleRefs(
                primary_request_id="req-1",
                primary_bundle_id="bundle-1",
            ),
            authoritative_snapshot_id="snap-1",
            audit=StorytellerAuditRecord(),
        )
        self.assertEqual(len(package.observations), 0)
        self.assertEqual(len(package.progression_opportunities), 0)

    def test_optional_sections_remain_valid_when_omitted(self) -> None:
        minimal = dict(CANONICAL_EXEMPLAR)
        parsed, err = parse_storyteller_assessment(minimal)
        self.assertIsNone(err)
        self.assertNotIn("active_tensions", parsed or {})

    def test_missing_schema_is_schema_mismatch(self) -> None:
        parsed, err = parse_storyteller_assessment({"observations": [{"text": "x"}]})
        self.assertIsNone(parsed)
        self.assertEqual(err, "schema_mismatch")

    def test_prohibited_fields_rejected(self) -> None:
        payload = dict(CANONICAL_EXEMPLAR)
        payload["dialogue"] = "forbidden"
        parsed, err = parse_storyteller_assessment(payload)
        self.assertIsNone(parsed)
        self.assertTrue(err and err.startswith("prohibited_fields:"))

    def test_provenance_digest_is_stable(self) -> None:
        first = storyteller_assessment_response_contract_provenance()
        second = storyteller_assessment_response_contract_provenance()
        self.assertEqual(first["response_contract_revision"], RESPONSE_CONTRACT_REVISION)
        self.assertEqual(first, second)
        self.assertEqual(len(first["response_contract_digest"]), 64)
        self.assertEqual(first["response_contract_digest"], response_contract_digest())

    def test_projected_text_includes_exemplar_and_vocabulary(self) -> None:
        text = project_storyteller_assessment_response_contract_text()
        self.assertIn('"schema": "hg_storyteller_assessment_v1"', text)
        self.assertIn("observations", text)
        self.assertIn("progression_opportunities", text)
        self.assertIn("opportunity_label", text)
        self.assertIn("narrative_hook", text)
        self.assertIn('Do not use top-level keys "assessment" or "opportunities"', text)
        self.assertIn("active_tensions", text)
        self.assertNotIn("evidence_refs", json.dumps(CANONICAL_EXEMPLAR))
        for field in ("next_actor", "dialogue", "narration", "structured_move"):
            self.assertIn(field, text)

    def test_prepare_includes_structural_and_behavioral_contributions(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        scene_id = kernel.create_scene().hg_scene_id
        round_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
        orient = kernel.prepare_storyteller_orientation_context(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-storyteller-146",
        )
        orientation_finalize = kernel.finalize_storyteller_orientation(
            hg_scene_id=scene_id,
            hg_round_id=round_id,
            inference_id="inf-storyteller-146",
            orientation_result={
                "schema": "hg_storyteller_orientation_v1",
                "information_gaps": ["What is happening?"],
            },
        )
        self.assertTrue(orientation_finalize["accepted"])
        bundle = {
            "bundle_id": "bundle-146",
            "request_id": "req-146",
            "entries": [],
            "satisfaction": {"focus_questions": []},
            "degradation": {"level": "none", "mode": "none"},
            "validity": {"validity_scope": "stage_current", "bound_hg_round_id": round_id},
        }
        prepared = kernel.prepare_storyteller_assessment_context(
            hg_scene_id=scene_id,
            inference_id="inf-storyteller-146",
            orientation=orientation_finalize["orientation"],
            bundle=bundle,
        )
        contributions = prepared["contributions"]
        instructions = [c for c in contributions if c["source_kind"] == "inference_instruction"]
        structural = next(
            c
            for c in instructions
            if c["contribution_id"].endswith("storyteller_assessment_response_contract")
        )
        behavioral = next(
            c for c in instructions if c["contribution_id"].endswith("storyteller_assessment_instruction")
        )
        self.assertEqual(structural["priority"], 28)
        self.assertEqual(behavioral["priority"], 100)
        self.assertLess(structural["priority"], behavioral["priority"])
        self.assertIn("response_contract_revision", structural["provenance"])
        self.assertIn("response_contract_digest", structural["provenance"])
        self.assertNotIn("response_contract_digest", behavioral["provenance"])
        self.assertIn(STORYTELLER_ASSESSMENT_SCHEMA, structural["content"])
        self.assertNotIn("Canonical exemplar", behavioral["content"])
        self.assertIn("STORYTELLER INFORMED ASSESSMENT TASK", behavioral["content"])
        priorities = [c["priority"] for c in contributions]
        self.assertEqual(priorities, [10, 28, 30, 100])

    def test_prohibited_fields_remain_shared_with_orientation(self) -> None:
        self.assertIn("dialogue", PROHIBITED_STORYTELLER_FIELDS)
        self.assertIn("next_actor", PROHIBITED_STORYTELLER_FIELDS)


if __name__ == "__main__":
    unittest.main()
