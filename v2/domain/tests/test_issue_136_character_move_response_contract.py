"""Issue #136 — canonical Character move response contract."""

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

from character_move_ingress import (  # noqa: E402
    V2_ROOT_ALLOWLIST,
    ingest_character_move_json_object,
    validate_canonical_v2,
)
from character_move_response_contract import (  # noqa: E402
    ACTION_BEAT_ALLOWED_KEYS,
    CANONICAL_EXEMPLAR,
    MOTIVATION_REQUIRED_FIELDS,
    PROHIBITED_BEAT_FIELD_NAMES,
    PROHIBITED_ROOT_KEYS,
    RISK_LEVEL_VALUES,
    SEMANTIC_EVALUATION_DECISIONS,
    SPEECH_BEAT_ALLOWED_KEYS,
    V2_ROOT_ALLOWLIST as CONTRACT_ROOT_ALLOWLIST,
    beat_allowed_keys_for_type,
    character_move_response_contract_provenance,
    project_character_move_response_contract_text,
    response_contract_digest,
)
from domain_api.contract import ContextPrepareRequest, RoundStartRequest  # noqa: E402
from domain_api.kernel import DomainKernel  # noqa: E402

APPROVED_CHARACTER_INVARIANT = (
    "Ground this turn's beats and motivation in the authoritative Character and "
    "scene context already supplied; action, inaction, and change should follow "
    "from that context."
)


class Issue136CharacterMoveResponseContractTests(unittest.TestCase):
    def test_contract_root_allowlist_matches_ingress(self) -> None:
        self.assertEqual(CONTRACT_ROOT_ALLOWLIST, V2_ROOT_ALLOWLIST)

    def test_beat_allowed_keys_match_ingress_expectations(self) -> None:
        self.assertEqual(beat_allowed_keys_for_type("action"), ACTION_BEAT_ALLOWED_KEYS)
        self.assertEqual(beat_allowed_keys_for_type("speech"), SPEECH_BEAT_ALLOWED_KEYS)
        self.assertFalse(PROHIBITED_BEAT_FIELD_NAMES & ACTION_BEAT_ALLOWED_KEYS)
        self.assertFalse(PROHIBITED_BEAT_FIELD_NAMES & SPEECH_BEAT_ALLOWED_KEYS)

    def test_projected_text_includes_exemplar_enums_and_prohibitions(self) -> None:
        text = project_character_move_response_contract_text()
        lower = text.lower()
        self.assertIn('"move_schema_version": 2', text)
        self.assertIn('"type": "action"', text)
        self.assertIn('"action":', text)
        self.assertIn('"type": "speech"', text)
        self.assertIn('"dialogue":', text)
        for field in MOTIVATION_REQUIRED_FIELDS:
            self.assertIn(field, lower)
        for level in sorted(RISK_LEVEL_VALUES):
            self.assertIn(level, lower)
        for decision in sorted(SEMANTIC_EVALUATION_DECISIONS):
            self.assertIn(decision, lower)
        self.assertIn("description", lower)
        self.assertIn("key", lower)
        for root_key in PROHIBITED_ROOT_KEYS:
            self.assertIn(root_key, lower)

    def test_canonical_exemplar_validates_through_ingress(self) -> None:
        move, err = ingest_character_move_json_object(dict(CANONICAL_EXEMPLAR))
        self.assertEqual(err, "")
        self.assertIsNotNone(move)
        self.assertEqual("", validate_canonical_v2(dict(CANONICAL_EXEMPLAR)))

    def test_provenance_digest_is_stable(self) -> None:
        first = character_move_response_contract_provenance()
        second = character_move_response_contract_provenance()
        self.assertEqual(first["response_contract_revision"], second["response_contract_revision"])
        self.assertEqual(first["response_contract_digest"], second["response_contract_digest"])
        self.assertEqual(len(first["response_contract_digest"]), 64)
        self.assertEqual(first["response_contract_digest"], response_contract_digest())

    def test_manifest_has_separate_structural_and_behavioral_contributions(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        scene_id = kernel.create_scene().hg_scene_id
        rnd_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
        manifest = kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=rnd_id,
                inference_id="inf-char-136-contract",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=0,
            )
        )
        instructions = [
            c for c in manifest.contributions if c.source_kind == "inference_instruction"
        ]
        self.assertEqual(len(instructions), 2)
        by_id = {c.contribution_id: c for c in instructions}
        structural = next(
            c for c in instructions if c.contribution_id.endswith("-response-contract")
        )
        behavioral = next(c for c in instructions if c.contribution_id.endswith("-instruction"))
        self.assertLess(structural.priority, behavioral.priority)
        self.assertIn('"move_schema_version": 2', structural.content)
        self.assertIn(APPROVED_CHARACTER_INVARIANT, behavioral.content)
        self.assertNotIn('"move_schema_version": 2', behavioral.content)
        self.assertIn(
            "response_contract_revision",
            structural.provenance,
        )
        self.assertIn(
            "response_contract_digest",
            structural.provenance,
        )
        self.assertNotIn("response_contract_digest", behavioral.provenance)
        self.assertEqual(
            structural.provenance["response_contract_digest"],
            response_contract_digest(),
        )

    def test_correction_attempt_preserves_response_contract_provenance(self) -> None:
        kernel = DomainKernel.for_fixture_store()
        scene_id = kernel.create_scene().hg_scene_id
        rnd_id = kernel.start_round(RoundStartRequest(hg_scene_id=scene_id)).hg_round_id
        correction = {
            "evaluation_pass_id": "eval-136",
            "validation_errors": ["semantic_evaluation.decision must be covered_change or no_covered_change"],
        }
        manifest = kernel.prepare_context(
            ContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=rnd_id,
                inference_id="inf-char-136-correction",
                character_id="Alice",
                role="guest",
                turn_index=0,
                attempt_index=1,
                correction_context=correction,
            )
        )
        structural = next(
            c
            for c in manifest.contributions
            if c.source_kind == "inference_instruction"
            and c.contribution_id.endswith("-response-contract")
        )
        correction_entries = [
            c for c in manifest.contributions if c.source_kind == "semantic_correction"
        ]
        self.assertTrue(correction_entries)
        self.assertEqual(
            structural.provenance["response_contract_digest"],
            response_contract_digest(),
        )
        self.assertEqual(
            structural.provenance["response_contract_revision"],
            character_move_response_contract_provenance()["response_contract_revision"],
        )


if __name__ == "__main__":
    unittest.main()
