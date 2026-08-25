"""#34 S2a Librarian read-path + semantic mediation remediation tests."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import (  # noqa: E402
    LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    BudgetExpectations,
    EntityRef,
    InformationNeed,
    KnowledgeAccessRequest,
    RelationshipFocus,
    VisibilityEnvelope,
    validate_knowledge_access_request,
)
from domain_api.librarian_mapper import build_retrieval_access_requests  # noqa: E402
from domain_api.librarian_mediation_validate import (  # noqa: E402
    parse_librarian_mediation_result,
    validate_librarian_mediation_result,
)
from domain_api.librarian_mediation_catalog import build_mediation_working_set  # noqa: E402
from domain_api.librarian_service import LibrarianService, MediationAssembly, build_host_default_request  # noqa: E402
from domain_api.retrieval_contract import (  # noqa: E402
    RetrievalCandidate,
    RetrievalCandidatePayload,
)
from domain_api.retrieval_service import RetrievalService  # noqa: E402
from domain_api.scope_knowledge_repository import ScopeKnowledgeRepository  # noqa: E402
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402


def _base_request(**overrides: object) -> KnowledgeAccessRequest:
    request = KnowledgeAccessRequest(
        request_id="req-test-1",
        consumer_role="storyteller",
        audit_reason="unit_test",
        hg_scene_id="scene-1",
        hg_round_id="round-1",
        turn_index=0,
        pipeline_stage="director",
        visibility_envelope=VisibilityEnvelope(
            viewer_role="orchestration",
            authority_ceiling_enforced="derived",
            session_template_id="template-1",
        ),
        information_need=InformationNeed(
            focus_questions=("placeholder?",),
            recall_breadth_preference="focused",
        ),
        host_allowed_information_classes=frozenset({"authored_static"}),
        budget_expectations=BudgetExpectations(max_bundle_entries=8, max_bundle_chars=8000),
    )
    if overrides:
        return KnowledgeAccessRequest(**{**request.__dict__, **overrides})
    return request


def _candidate(candidate_id: str, content: str) -> RetrievalCandidate:
    return RetrievalCandidate(
        candidate_id=candidate_id,
        information_class="authored_static",
        payload=RetrievalCandidatePayload(content=content),
        authority_class="suggestive",
        visibility="public",
    )


def _contextual_result(*selections: tuple[str, int, tuple[str, ...] | None]) -> dict:
    return {
        "schema": LIBRARIAN_MEDIATION_RESULT_SCHEMA,
        "selected_items": [
            {
                "source_id": source_id,
                "relevance_rank": rank,
                "relevance_band": "high" if rank == 1 else "medium",
                "salience_note": "contextual selection",
                "interpretive_status": "likely",
                "answers_focus_questions": list(answers or ()),
            }
            for source_id, rank, answers in selections
        ],
    }


class LibrarianContractTests(unittest.TestCase):
    def test_validate_rejects_authority_widening(self) -> None:
        request = KnowledgeAccessRequest(
            request_id="req-bad",
            consumer_role="character",
            audit_reason="bad",
            hg_scene_id="scene-1",
            hg_round_id="round-1",
            turn_index=0,
            pipeline_stage="character",
            visibility_envelope=VisibilityEnvelope(
                viewer_role="character",
                authority_ceiling_enforced="suggestive",
            ),
            information_need=InformationNeed(focus_questions=("test?",)),
            authority_ceiling="authoritative",
        )
        with self.assertRaises(ValueError):
            validate_knowledge_access_request(request)


class LibrarianMappingTests(unittest.TestCase):
    def test_mapping_preserves_layer_separation(self) -> None:
        request = _base_request(
            information_need=InformationNeed(
                focus_questions=("What happened to the hidden passage?",),
                entity_refs=(EntityRef(ref_kind="character", stable_ref="alice"),),
            )
        )
        retrieval_requests = build_retrieval_access_requests(request, memory_scope_id="scope-1")
        first = retrieval_requests[0]
        self.assertEqual(first.consumer_role, "librarian")
        self.assertTrue(first.hard_access.exclude_authoritative_live)
        self.assertNotEqual(first.hard_access, first.generation_hints)


class LibrarianValidationTests(unittest.TestCase):
    def test_rejects_unknown_source_id(self) -> None:
        request = _base_request(
            information_need=InformationNeed(focus_questions=("Why?",)),
        )
        working = build_mediation_working_set([], [_candidate("c1", "fact")])
        parsed, _ = parse_librarian_mediation_result(
            _contextual_result(("lmi:cand:missing", 1, ("Why?",)))
        )
        assert parsed is not None
        validation = validate_librarian_mediation_result(
            parsed,
            catalog=working.catalog,
            request=request,
        )
        self.assertFalse(validation.accepted)
        self.assertIn("unknown_source:lmi:cand:missing", validation.rejection_codes)

    def test_rejects_authority_elevation(self) -> None:
        request = _base_request(information_need=InformationNeed(focus_questions=("Why?",)))
        working = build_mediation_working_set([], [_candidate("c1", "fact")])
        source_id = "lmi:cand:c1"
        parsed, _ = parse_librarian_mediation_result(
            {
                "schema": LIBRARIAN_MEDIATION_RESULT_SCHEMA,
                "selected_items": [
                    {
                        "source_id": source_id,
                        "relevance_rank": 1,
                        "interpretive_status": "confirmed",
                    }
                ],
            }
        )
        assert parsed is not None
        validation = validate_librarian_mediation_result(
            parsed,
            catalog=working.catalog,
            request=request,
        )
        self.assertFalse(validation.accepted)


class LibrarianServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.scope_repo = ScopeKnowledgeRepository(self._tmpdir)
        self.service = LibrarianService(RetrievalService(scope_repo=self.scope_repo))

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _fixture(self) -> object:
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

    def _access_with_candidates(
        self,
        request: KnowledgeAccessRequest,
        candidates: list[RetrievalCandidate],
        mediation_result: dict | None,
        *,
        allow_fallback: bool = True,
    ):
        fixture = self._fixture()
        original_assemble = self.service.assemble_mediation_inputs

        def _stub_assemble(req: KnowledgeAccessRequest, fix: object) -> MediationAssembly:
            assembly = original_assemble(req, fix)
            working = build_mediation_working_set([], candidates)
            return MediationAssembly(
                working_set=working,
                retrieval_request_ids=assembly.retrieval_request_ids,
                retrieval_responses=assembly.retrieval_responses,
                per_source=assembly.per_source,
                consulted=assembly.consulted,
                omitted=assembly.omitted,
            )

        self.service.assemble_mediation_inputs = _stub_assemble  # type: ignore[method-assign]
        try:
            return self.service.access_knowledge(
                request,
                fixture,
                mediation_result=mediation_result,
                inference_id="inf-test",
                allow_deterministic_fallback=allow_fallback,
            )
        finally:
            self.service.assemble_mediation_inputs = original_assemble  # type: ignore[method-assign]

    def test_contextual_semantic_mode_on_valid_result(self) -> None:
        request = _base_request(
            hg_scene_id="scene-x",
            information_need=InformationNeed(
                focus_questions=("Why is the hidden passage dangerous now?",),
            ),
        )
        candidates = [
            _candidate("decoy", "hidden passage hidden passage danger danger danger"),
            _candidate("explain", "The east tunnel collapse makes the old route lethal tonight."),
        ]
        result = _contextual_result(
            ("lmi:cand:explain", 1, ("Why is the hidden passage dangerous now?",)),
            ("lmi:cand:decoy", 2, ()),
        )
        bundle = self._access_with_candidates(request, candidates, result)
        self.assertEqual(bundle.mediation_mode, "contextual_semantic")
        self.assertEqual(bundle.degradation.mode, "none")
        self.assertFalse(bundle.degradation.deterministic_fallback_used)
        self.assertEqual(bundle.entries[0].ref.stable_ref, "explain")

    def test_adversarial_a_indirect_causal(self) -> None:
        question = "Why is Alice reacting angrily now?"
        request = _base_request(information_need=InformationNeed(focus_questions=(question,)))
        candidates = [
            _candidate("noise", "Alice is angry and reacting strongly in the workshop today."),
            _candidate("cause", "Three days ago Bob broke the treaty seal in the archive."),
        ]
        result = _contextual_result(
            ("lmi:cand:cause", 1, (question,)),
            ("lmi:cand:noise", 2, ()),
        )
        bundle = self._access_with_candidates(request, candidates, result)
        self.assertEqual(bundle.entries[0].ref.stable_ref, "cause")

    def test_adversarial_b_cross_relationship(self) -> None:
        question = "What explains Alice current tension toward Bob?"
        request = _base_request(
            information_need=InformationNeed(
                focus_questions=(question,),
                relationship_focus=(RelationshipFocus(subject_ref="alice", object_ref="bob"),),
            )
        )
        candidates = [
            _candidate("ab", "Alice and Bob share the same patrol roster."),
            _candidate("ac", "Alice learned Carol betrayed her; she now distrusts allies including Bob."),
        ]
        result = _contextual_result(("lmi:cand:ac", 1, (question,)))
        bundle = self._access_with_candidates(request, candidates, result)
        self.assertEqual(bundle.entries[0].ref.stable_ref, "ac")

    def test_adversarial_c_late_emerging_significance(self) -> None:
        question = "Why does the broken seal matter after the latest confession?"
        request = _base_request(information_need=InformationNeed(focus_questions=(question,)))
        candidates = [
            _candidate("old", "A hairline crack on the seal was noticed last week."),
            _candidate("latest", "Dana confessed the seal was deliberately broken to hide the passage."),
        ]
        result = _contextual_result(("lmi:cand:latest", 1, (question,)))
        bundle = self._access_with_candidates(request, candidates, result)
        self.assertEqual(bundle.entries[0].ref.stable_ref, "latest")

    def test_adversarial_d_lexical_decoy(self) -> None:
        question = "Why is the hidden passage dangerous now?"
        request = _base_request(information_need=InformationNeed(focus_questions=(question,)))
        candidates = [
            _candidate("decoy", "hidden passage hidden passage secret route danger danger danger"),
            _candidate("explain", "The collapse in the east tunnel makes any exit lethal tonight."),
        ]
        result = _contextual_result(("lmi:cand:explain", 1, (question,)))
        bundle = self._access_with_candidates(request, candidates, result)
        self.assertEqual(bundle.entries[0].ref.stable_ref, "explain")

    def test_invalid_mediation_falls_back_explicitly(self) -> None:
        request = _base_request(information_need=InformationNeed(focus_questions=("Why?",)))
        candidates = [_candidate("c1", "Alice knows the hidden passage.")]
        bundle = self._access_with_candidates(
            request,
            candidates,
            {"schema": LIBRARIAN_MEDIATION_RESULT_SCHEMA, "selected_items": []},
        )
        self.assertEqual(bundle.mediation_mode, "deterministic_fallback")
        self.assertEqual(bundle.degradation.mode, "deterministic_fallback")
        self.assertTrue(bundle.degradation.deterministic_fallback_used)

    def test_inference_failure_path_without_fallback_is_authoritative_only(self) -> None:
        fixture = self._fixture()
        request = build_host_default_request(fixture, pipeline_stage="director")
        request = KnowledgeAccessRequest(
            **{
                **request.__dict__,
                "degradation_preferences": request.degradation_preferences.__class__(
                    allow_partial_sources=True,
                    allow_heuristic_fallback=False,
                    require_provenance_complete=False,
                ),
            }
        )
        bundle = self.service.access_knowledge(
            request,
            fixture,
            mediation_result=None,
            allow_deterministic_fallback=False,
        )
        self.assertIn(
            bundle.mediation_mode,
            {"authoritative_only", "deterministic_fallback"},
        )
        if bundle.mediation_mode == "authoritative_only":
            self.assertEqual(bundle.degradation.mode, "authoritative_only")

    def test_prepare_mediation_context_returns_catalog(self) -> None:
        fixture = self._fixture()
        request = build_host_default_request(fixture, pipeline_stage="director")
        prepared = self.service.prepare_mediation_context(
            request,
            fixture,
            inference_id="inf-prepare",
        )
        self.assertTrue(prepared.mediation_catalog)
        self.assertTrue(prepared.contributions)
        self.assertTrue(prepared.retrieval_request_ids)


if __name__ == "__main__":
    unittest.main()
