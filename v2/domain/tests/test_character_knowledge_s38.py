"""#38 Character knowledge-orientation and epistemic boundary tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.character_contract import (  # noqa: E402
    CHARACTER_ORIENTATION_SCHEMA,
    orientation_to_knowledge_access_request,
    parse_character_orientation,
)
from domain_api.character_epistemic import (  # noqa: E402
    build_character_visibility_envelope,
    character_may_know_candidate,
)
from domain_api.character_knowledge_validity import build_character_knowledge_reuse_key  # noqa: E402
from domain_api.character_service import CharacterKnowledgeService  # noqa: E402
from domain_api.librarian_contract import (  # noqa: E402
    InformationNeed,
    KnowledgeAccessRequest,
    VisibilityEnvelope,
    validate_knowledge_access_request,
)
from domain_api.librarian_packaging_mapper import map_librarian_bundle_to_contributions  # noqa: E402
from domain_api.librarian_packaging_policy import policy_for_consumer  # noqa: E402
from domain_api.librarian_packaging_validity import PackagingBindingContext  # noqa: E402
from domain_api.retrieval_contract import (  # noqa: E402
    HardAccessConstraints,
    RetrievalAccessDiagnostics,
    RetrievalCandidate,
    RetrievalCandidatePayload,
)
from domain_api.retrieval_service import _hard_access_allows  # noqa: E402
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402
from domain.tests.test_librarian_packaging_s2b import _bundle  # noqa: E402


def _valid_orientation(**overrides: object) -> dict:
    payload = {
        "schema": CHARACTER_ORIENTATION_SCHEMA,
        "orientation_id": "char-orient-1",
        "hg_round_id": "round-1",
        "turn_index": 0,
        "character_id": "Alice",
        "information_gaps": ("What do I know about the treaty?",),
        "temporal_focus": "current",
        "breadth_preference": "focused",
    }
    payload.update(overrides)
    return payload


class CharacterKnowledgeS38Tests(unittest.TestCase):
    def test_parse_orientation_requires_character_and_gaps(self) -> None:
        orientation, error = parse_character_orientation(_valid_orientation())
        self.assertIsNone(error)
        assert orientation is not None
        self.assertEqual(orientation.character_id, "Alice")
        self.assertEqual(len(orientation.information_gaps), 1)

        bad, bad_error = parse_character_orientation(_valid_orientation(information_gaps=[]))
        self.assertIsNone(bad)
        self.assertEqual(bad_error, "information_gaps_required")

    def test_orientation_kar_uses_character_consumer(self) -> None:
        orientation, _ = parse_character_orientation(_valid_orientation())
        assert orientation is not None
        envelope = {
            "viewer_character_id": "Alice",
            "subject_character_id": "Alice",
            "known_by_snapshot_id": "known_by:Alice:abc",
        }
        kar = orientation_to_knowledge_access_request(
            orientation,
            hg_scene_id="scene-1",
            request_id="req-1",
            visibility_envelope=envelope,
        )
        self.assertEqual(kar.consumer_role, "character")
        self.assertEqual(kar.consumer_instance_id, "Alice")
        self.assertEqual(kar.pipeline_stage, "character")

    def test_known_by_candidate_rejection(self) -> None:
        allowed = character_may_know_candidate(
            character_id="Alice",
            provenance={"known_by": ["Bob"]},
            host_internal_metadata=None,
        )
        self.assertFalse(allowed)
        allowed_alice = character_may_know_candidate(
            character_id="Alice",
            provenance={"known_by": ["Alice", "Bob"]},
            host_internal_metadata=None,
        )
        self.assertTrue(allowed_alice)

    def test_hard_access_known_by_filter(self) -> None:
        candidate = RetrievalCandidate(
            candidate_id="c1",
            information_class="authored_static",
            payload=RetrievalCandidatePayload(content="secret"),
            authority_class="suggestive",
            visibility="public",
            provenance={"known_by": ["Bob"]},
        )
        diagnostics = RetrievalAccessDiagnostics()
        hard = HardAccessConstraints(known_by_character_name="Alice")
        allowed = _hard_access_allows(
            candidate,
            hard,
            character_file_ids={},
            diagnostics=diagnostics,
        )
        self.assertFalse(allowed)

    def test_character_rejects_deterministic_fallback_packaging(self) -> None:
        from domain_api.librarian_contract import (
            BundleValidity,
            InvalidationKey,
            LibrarianAnnotation,
            LibrarianBundleEntry,
            StableReference,
        )

        binding = PackagingBindingContext(
            hg_round_id="round-1",
            turn_index=0,
            pipeline_stage="character",
            continuity_version=3,
            authoritative_snapshot_id="cv:3:scene:scene-1:round:round-1",
            bound_character_id="Alice",
        )
        validity = BundleValidity(
            validity_scope="stage_current",
            bound_hg_round_id="round-1",
            bound_turn_index=0,
            bound_pipeline_stage="character",
            valid_from_authoritative_snapshot_id=binding.authoritative_snapshot_id,
            invalidation_keys=(
                InvalidationKey(key_kind="continuity_version", key_value="3"),
                InvalidationKey(key_kind="hg_round_id", key_value="round-1"),
                InvalidationKey(key_kind="pipeline_stage", key_value="character"),
            ),
        )
        entry = LibrarianBundleEntry(
            entry_id="e1",
            ref=StableReference(ref_kind="retrieval", stable_ref="ref-1"),
            content="fact",
            authority_class="suggestive",
            information_class="authored_static",
            visibility_scope="public",
            source_tier="authored_static",
            provenance={"candidate_id": "e1"},
            temporal_relationship="recent",
            librarian_annotation=LibrarianAnnotation(relevance_rank=1),
        )
        bundle = _bundle(
            entries=(entry,),
            mediation_mode="deterministic_fallback",
            validity=validity,
        )
        bundle = bundle.__class__(
            **{
                **bundle.__dict__,
                "pipeline_stage": "character",
                "consumer_role": "character",
            }
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-1",
            consumer_target="character",
            binding=binding,
            policy=policy_for_consumer("character"),
        )
        self.assertEqual(result.contributions, ())
        self.assertIn("deterministic_fallback", str(result.omitted_reason))

    def test_character_binding_mismatch_rejected(self) -> None:
        bundle = _bundle(entries=())
        bundle = bundle.__class__(
            **{
                **bundle.__dict__,
                "consumer_role": "character",
                "audit": bundle.audit.__class__(
                    **{
                        **bundle.audit.__dict__,
                        "structured_mediation_evidence": {"consumer_instance_id": "Bob"},
                    }
                ),
            }
        )
        binding = PackagingBindingContext(
            hg_round_id="round-1",
            turn_index=0,
            pipeline_stage="character",
            continuity_version=3,
            authoritative_snapshot_id="cv:3:scene:scene-1:round:round-1",
            bound_character_id="Alice",
        )
        result = map_librarian_bundle_to_contributions(
            bundle,
            manifest_id="manifest-1",
            consumer_target="character",
            binding=binding,
        )
        self.assertEqual(result.contributions, ())
        self.assertIn("character_binding_mismatch", result.eligibility.rejection_codes)

    def test_reuse_key_changes_with_correction(self) -> None:
        base = build_character_knowledge_reuse_key(
            character_id="Alice",
            hg_round_id="round-1",
            turn_index=0,
            continuity_version=1,
            upstream_fingerprint="abc",
            director_decision=None,
            correction_context=None,
            kar_fingerprint="kar",
        )
        with_correction = build_character_knowledge_reuse_key(
            character_id="Alice",
            hg_round_id="round-1",
            turn_index=0,
            continuity_version=1,
            upstream_fingerprint="abc",
            director_decision=None,
            correction_context={"reason": "soft"},
            kar_fingerprint="kar",
        )
        self.assertNotEqual(base, with_correction)

    def test_no_legacy_character_knowledge_production_path(self) -> None:
        kernel_path = Path(__file__).resolve().parents[2] / "domain_api" / "kernel.py"
        source = kernel_path.read_text(encoding="utf-8")
        prepare_block = source.split("def prepare_context(", 1)[1].split("\n    def ", 1)[0]
        self.assertNotIn("project_context", prepare_block)
        self.assertNotIn("authored_character_knowledge", prepare_block)
        adapter_path = Path(__file__).resolve().parents[2] / "domain_api" / "character_retrieval_adapter.py"
        self.assertFalse(adapter_path.exists())


class CharacterKnowledgeServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = CharacterKnowledgeService()

    def _fixture(self):
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.setup_snapshot = {
            "scene_template_id": "test_template",
            "character_cards": {"alice": {"lore_facts": ["Alice knows the hidden passage."]}},
        }
        fixture.memory_scope_id = "scope-test"
        fixture.character_file_ids = {"Alice": "alice", "Bob": "bob"}
        fixture.rounds.append(
            RoundFixture(
                hg_round_id="round-1",
                hg_scene_id=fixture.hg_scene_id,
                turn_index=0,
            )
        )
        return fixture

    def test_finalize_orientation_produces_character_kar(self) -> None:
        fixture = self._fixture()
        rnd = fixture.rounds[-1]
        finalized = self.service.finalize_orientation(
            fixture,
            rnd,
            inference_id="inf-1",
            character_id="Alice",
            turn_index=0,
            orientation_result=_valid_orientation(hg_round_id=rnd.hg_round_id),
            upstream_fingerprint="upstream-fp-test",
            director_decision=None,
            correction_context=None,
        )
        self.assertTrue(finalized["accepted"])
        self.assertEqual(finalized["reason"], "ok")
        orientation = finalized["orientation"]
        self.assertEqual(orientation["character_id"], "Alice")
        self.assertEqual(orientation["orientation_id"], "char-orient-1")
        kar = finalized["knowledge_access_request"]
        assert kar is not None
        self.assertEqual(kar["consumer_role"], "character")
        self.assertEqual(kar["consumer_instance_id"], "Alice")
        self.assertEqual(kar["pipeline_stage"], "character")
        validate_knowledge_access_request(
            KnowledgeAccessRequest(
                request_id=kar["request_id"],
                consumer_role=kar["consumer_role"],
                audit_reason=kar["audit_reason"],
                hg_scene_id=fixture.hg_scene_id,
                hg_round_id=kar["hg_round_id"],
                turn_index=kar["turn_index"],
                pipeline_stage=kar["pipeline_stage"],
                visibility_envelope=VisibilityEnvelope(
                    viewer_role=kar["visibility_envelope"]["viewer_role"],
                    authority_ceiling_enforced=kar["visibility_envelope"]["authority_ceiling_enforced"],
                    session_template_id=kar["visibility_envelope"].get("session_template_id"),
                ),
                information_need=InformationNeed(
                    focus_questions=tuple(kar["information_need"]["focus_questions"]),
                    recall_breadth_preference=kar["information_need"]["recall_breadth_preference"],
                ),
                host_allowed_information_classes=frozenset(kar["host_allowed_information_classes"]),
            )
        )


if __name__ == "__main__":
    unittest.main()
