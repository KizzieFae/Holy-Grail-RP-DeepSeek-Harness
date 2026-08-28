"""Issue #50 story knowledge storage, retrieval, and mediation tests."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from continuity_state import PublicEvent  # noqa: E402
from domain_api.knowledge_service import KnowledgeService  # noqa: E402
from domain_api.librarian_contract import (  # noqa: E402
    BudgetExpectations,
    InformationNeed,
    KnowledgeAccessRequest,
    VisibilityEnvelope,
)
from domain_api.librarian_service import LibrarianService  # noqa: E402
from domain_api.retrieval_contract import (  # noqa: E402
    GenerationHints,
    HardAccessConstraints,
    ResponseBudget,
    RetrievalAccessRequest,
)
from domain_api.retrieval_service import RetrievalService  # noqa: E402
from domain_api.scope_knowledge_repository import ScopeKnowledgeRepository  # noqa: E402
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402
from domain_api.story_knowledge_contract import (  # noqa: E402
    DerivedStoryRecordSubmission,
    EpistemicAuthorityRef,
    StableRef,
    StoryEvidence,
)
from domain_api.story_knowledge_epistemic import resolve_epistemic_authority_ref  # noqa: E402
from domain_api.story_knowledge_repository import StoryKnowledgeRepository  # noqa: E402
from domain_api.story_knowledge_service import StoryKnowledgeService  # noqa: E402
from domain_api.story_semantic_index import (  # noqa: E402
    DeterministicHashEmbeddingProvider,
    SemanticIndexBackend,
    TfidfEmbeddingProvider,
)


def _event(
    event_id: str,
    summary: str,
    *,
    turn_index: int = 1,
    known_by: list[str] | None = None,
    stable_ref: str | None = None,
) -> PublicEvent:
    markers = [stable_ref] if stable_ref else []
    return PublicEvent(
        event_id=event_id,
        timestamp=datetime.now(timezone.utc),
        event_type="dialogue",
        participants=["Alice"],
        summary=summary,
        turn_index=turn_index,
        known_by=list(known_by or ["Alice"]),
        grounding_markers=markers,
    )


class StoryKnowledgePersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = StoryKnowledgeRepository(self._tmpdir)
        self.service = StoryKnowledgeService(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _fixture(self, scope: str = "scope-a") -> object:
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.memory_scope_id = scope
        fixture.manager.public_events.append(
            _event("evt-1", "Alice said Rin lives in Kyoto.", known_by=["Alice"])
        )
        return fixture

    def test_append_restart_idempotent(self) -> None:
        fixture = self._fixture()
        first = self.service.project_after_commit(fixture, source_domain_commit_id="commit-1")
        second = self.service.project_after_commit(fixture, source_domain_commit_id="commit-1")
        self.assertEqual(first["appended"], 1)
        self.assertEqual(second["appended"], 0)
        records = self.repo.list_records("scope-a")
        self.assertEqual(len(records), 1)

    def test_truncated_tail_recovery(self) -> None:
        fixture = self._fixture()
        self.service.project_after_commit(fixture, source_domain_commit_id="commit-1")
        path = self.repo.records_path("scope-a")
        with open(path, "ab") as handle:
            handle.write(b"{broken json\n")
        count = self.service.recover_scope("scope-a")
        self.assertEqual(count, 1)

    def test_rebuild_index_from_jsonl_only(self) -> None:
        fixture = self._fixture()
        self.service.project_after_commit(fixture, source_domain_commit_id="commit-1")
        index_path = self.repo.semantic_index_path("scope-a")
        index_path.unlink()
        rebuilt = self.service.rebuild_semantic_index("scope-a")
        self.assertEqual(rebuilt, 1)
        index = SemanticIndexBackend(index_path=index_path)
        self.assertTrue(index.available)


class StoryKnowledgeRetrievalTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = StoryKnowledgeRepository(self._tmpdir)
        self.service = StoryKnowledgeService(self.repo)
        self.retrieval = RetrievalService(story_knowledge_repo=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _populate_lies(self, scope: str = "scope-lies") -> object:
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.memory_scope_id = scope
        for index in range(3):
            fixture.manager.public_events.append(
                _event(
                    f"lie-{index}",
                    f"Alice falsely claimed the emerald is hidden under bench {index}.",
                    turn_index=index + 1,
                    known_by=["Alice", "Bob"],
                )
            )
        self.service.project_after_commit(fixture, source_domain_commit_id="commit-lies")
        return fixture

    def _request(
        self,
        fixture: object,
        *,
        query: str,
        budget_chars: int = 32000,
        viewer: str = "Alice",
    ) -> RetrievalAccessRequest:
        return RetrievalAccessRequest(
            request_id="req-story",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id="round-1",
            turn_index=1,
            memory_scope_id=fixture.memory_scope_id,
            hard_access=HardAccessConstraints(
                known_by_character_name=viewer,
                allowed_information_classes=frozenset({"story_occurrence"}),
            ),
            generation_hints=GenerationHints(query_terms=(query,)),
            response_budget=ResponseBudget(max_candidates=32, max_total_chars=budget_chars),
        )

    def test_same_occurrence_multiple_semantic_aspects(self) -> None:
        fixture = initialize_live_session(cast=["Alice"])
        fixture.memory_scope_id = "scope-aspects"
        fixture.manager.public_events.append(
            _event(
                "evt-rich",
                "Alice photographed the bronze key beside the garden gate at dusk.",
                known_by=["Alice"],
                stable_ref="object:bronze_key",
            )
        )
        self.service.project_after_commit(fixture, source_domain_commit_id="c1")
        for query in ("bronze key photograph", "garden gate dusk", "Alice evening photo"):
            response = self.retrieval.retrieve(self._request(fixture, query=query), fixture)
            ids = {candidate.candidate_id for candidate in response.candidates}
            self.assertIn("evt-rich", ids)

    def test_repeated_lies_remain_distinct(self) -> None:
        fixture = self._populate_lies()
        response = self.retrieval.retrieve(
            self._request(fixture, query="emerald hidden bench"),
            fixture,
        )
        ids = {candidate.candidate_id for candidate in response.candidates}
        self.assertEqual(ids, {"lie-0", "lie-1", "lie-2"})

    def test_forbidden_then_propagated(self) -> None:
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.memory_scope_id = "scope-epi"
        event = _event("secret-evt", "Bob whispered the vault code.", known_by=["Bob"])
        fixture.manager.public_events.append(event)
        self.service.project_after_commit(fixture, source_domain_commit_id="c1")
        blocked = self.retrieval.retrieve(self._request(fixture, query="vault code", viewer="Alice"), fixture)
        self.assertEqual(len(blocked.candidates), 0)
        event.known_by.append("Alice")
        allowed = self.retrieval.retrieve(self._request(fixture, query="vault code", viewer="Alice"), fixture)
        self.assertEqual(len(allowed.candidates), 1)

    def test_scope_isolation(self) -> None:
        fixture_a = initialize_live_session(cast=["Alice"])
        fixture_a.memory_scope_id = "scope-a"
        fixture_a.manager.public_events.append(_event("evt-a", "Scope A secret.", known_by=["Alice"]))
        fixture_b = initialize_live_session(cast=["Alice"])
        fixture_b.memory_scope_id = "scope-b"
        self.service.project_after_commit(fixture_a, source_domain_commit_id="c-a")
        response = self.retrieval.retrieve(self._request(fixture_b, query="Scope A secret"), fixture_b)
        self.assertEqual(len(response.candidates), 0)

    def test_full_eligible_path(self) -> None:
        fixture = self._populate_lies()
        response = self.retrieval.retrieve(
            self._request(fixture, query="emerald", budget_chars=100000),
            fixture,
        )
        self.assertEqual(response.diagnostics.story_selection_path, "full_eligible")

    def test_semantic_ranked_path(self) -> None:
        fixture = self._populate_lies()
        response = self.retrieval.retrieve(
            self._request(fixture, query="bench 2 emerald", budget_chars=120),
            fixture,
        )
        self.assertEqual(response.diagnostics.story_selection_path, "semantic_ranked")
        self.assertGreaterEqual(len(response.candidates), 1)

    def test_missing_index_is_retrieval_failure_not_no_match(self) -> None:
        fixture = self._populate_lies()
        index_path = self.repo.semantic_index_path(fixture.memory_scope_id)
        if index_path.exists():
            index_path.unlink()
        response = self.retrieval.retrieve(
            self._request(fixture, query="bench emerald", budget_chars=50),
            fixture,
        )
        self.assertTrue(response.diagnostics.story_semantic_index_failed)
        self.assertEqual(len(response.candidates), 0)


class DerivedRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = StoryKnowledgeRepository(self._tmpdir)
        self.service = StoryKnowledgeService(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_derived_record_persists_with_authority_ref(self) -> None:
        submission = DerivedStoryRecordSubmission(
            story_record_id="derived-1",
            memory_scope_id="scope-derived",
            source_domain_commit_id="commit-d",
            source_session_id="session-1",
            hg_scene_id="scene-1",
            source_event_ids=("evt-1",),
            stable_refs=(StableRef(ref_kind="character", stable_ref="char:rin"),),
            evidence=StoryEvidence(None, "Rin moved to Osaka."),
            epistemic_authority_ref=EpistemicAuthorityRef(
                ref_kind="establishment_decision",
                ref_payload={"decision_id": "dec-1", "authorized": True, "allowed_viewers": ["Alice"]},
            ),
            submission_authority_ref="fixture-establishment",
        )
        self.assertTrue(self.service.submit_derived_record(submission))
        record = self.repo.get_record("scope-derived", "derived-1")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record.record_kind, "derived")

    def test_inherit_source_events_does_not_auto_imply_knowledge(self) -> None:
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.memory_scope_id = "scope-inherit"
        fixture.manager.public_events.append(
            _event("src-1", "Alice knows the passphrase.", known_by=["Alice"])
        )
        authority = EpistemicAuthorityRef(
            ref_kind="inherit_source_events",
            ref_payload={"event_ids": ["src-1"], "inherit_mode": "all_source_events_known"},
        )
        self.assertFalse(
            resolve_epistemic_authority_ref(
                fixture,
                authority,
                viewer_character_id="Bob",
            )
        )


class EmbeddingEvaluationTests(unittest.TestCase):
    def test_tfidf_beats_hash_on_lexical_collision(self) -> None:
        provider_hash = DeterministicHashEmbeddingProvider()
        provider_tfidf = TfidfEmbeddingProvider()
        relevant = "Alice photographed the bronze key beside the garden gate."
        irrelevant = "Alice bench emerald hidden falsely claimed under bench."
        query = "bronze key garden photograph"
        hash_rel = provider_hash.embed(relevant)
        hash_irr = provider_hash.embed(irrelevant)
        tfidf_rel = provider_tfidf.embed(relevant)
        tfidf_irr = provider_tfidf.embed(irrelevant)
        query_hash = provider_hash.embed(query)
        query_tfidf = provider_tfidf.embed(query)
        from domain_api.story_semantic_index import cosine_similarity

        hash_scores = (
            cosine_similarity(query_hash, hash_rel),
            cosine_similarity(query_hash, hash_irr),
        )
        tfidf_scores = (
            cosine_similarity(query_tfidf, tfidf_rel),
            cosine_similarity(query_tfidf, tfidf_irr),
        )
        self.assertGreater(tfidf_scores[0], tfidf_scores[1])


class AuthoredStoryPrecedenceTests(unittest.TestCase):
    def test_authored_snapshot_unchanged_after_projection(self) -> None:
        story_repo = StoryKnowledgeRepository(tempfile.mkdtemp())
        service = StoryKnowledgeService(story_repo)
        fixture = initialize_live_session(cast=["Alice"])
        fixture.memory_scope_id = "scope-immutable"
        original = {"character_cards": {"alice": {"lore_facts": ["Rin lives in Kyoto."]}}}
        fixture.setup_snapshot = json.loads(json.dumps(original))
        fixture.manager.public_events.append(
            _event("progression-1", "Rin moved to Osaka.", known_by=["Alice"])
        )
        service.project_after_commit(fixture, source_domain_commit_id="c1")
        self.assertEqual(fixture.setup_snapshot, original)

    def test_claim_does_not_supersede_authored_fact(self) -> None:
        """A statement occurrence is retrievable without mutating authored baseline."""
        story_repo = StoryKnowledgeRepository(tempfile.mkdtemp())
        retrieval = RetrievalService(story_knowledge_repo=story_repo)
        fixture = initialize_live_session(cast=["Alice"])
        fixture.memory_scope_id = "scope-claim"
        fixture.setup_snapshot = {
            "character_cards": {"alice": {"lore_facts": ["Rin lives in Kyoto."]}},
        }
        fixture.manager.public_events.append(
            _event(
                "claim-1",
                "Kizzie told Ayame that Rin lives in Osaka.",
                known_by=["Alice"],
            )
        )
        StoryKnowledgeService(story_repo).project_after_commit(fixture, source_domain_commit_id="c1")
        request = RetrievalAccessRequest(
            request_id="claim",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id="round-1",
            turn_index=1,
            memory_scope_id=fixture.memory_scope_id,
            hard_access=HardAccessConstraints(
                viewer_character_id="Alice",
                allowed_information_classes=frozenset({"authored_static", "story_occurrence"}),
            ),
            generation_hints=GenerationHints(query_terms=("Rin lives",)),
        )
        response = retrieval.retrieve(request, fixture)
        classes = {candidate.information_class for candidate in response.candidates}
        self.assertIn("authored_static", classes)
        self.assertIn("story_occurrence", classes)
        self.assertEqual(
            fixture.setup_snapshot["character_cards"]["alice"]["lore_facts"],
            ["Rin lives in Kyoto."],
        )

    def test_authored_and_story_both_retrievable_with_provenance(self) -> None:
        scope_tmp = tempfile.mkdtemp()
        try:
            scope_repo = ScopeKnowledgeRepository(scope_tmp)
            story_repo = StoryKnowledgeRepository(tempfile.mkdtemp())
            retrieval = RetrievalService(scope_repo=scope_repo, story_knowledge_repo=story_repo)
            fixture = initialize_live_session(cast=["Alice"])
            fixture.memory_scope_id = "scope-mix"
            fixture.setup_snapshot = {
                "character_cards": {"alice": {"lore_facts": ["Rin lives in Kyoto."]}},
            }
            fixture.manager.public_events.append(
                _event("move-osaka", "Rin moved to Osaka.", known_by=["Alice"])
            )
            StoryKnowledgeService(story_repo).project_after_commit(fixture, source_domain_commit_id="c1")
            request = RetrievalAccessRequest(
                request_id="mix",
                consumer_role="librarian",
                hg_scene_id=fixture.hg_scene_id,
                hg_round_id="round-1",
                turn_index=1,
                memory_scope_id=fixture.memory_scope_id,
                hard_access=HardAccessConstraints(
                    viewer_character_id="Alice",
                    known_by_character_name="Alice",
                    allowed_information_classes=frozenset(
                        {"authored_static", "story_occurrence"}
                    ),
                ),
                generation_hints=GenerationHints(query_terms=("Rin residence",)),
            )
            response = retrieval.retrieve(request, fixture)
            domains = {
                candidate.provenance.get("provenance_domain", candidate.provenance.get("source_kind"))
                for candidate in response.candidates
            }
            self.assertTrue(
                any(candidate.information_class == "authored_static" for candidate in response.candidates)
            )
            self.assertTrue(
                any(candidate.information_class == "story_occurrence" for candidate in response.candidates)
            )
            self.assertIn("story", domains)
        finally:
            shutil.rmtree(scope_tmp, ignore_errors=True)


class FailureSemanticsTests(unittest.TestCase):
    def test_librarian_mediation_outcome_retrieval_failure(self) -> None:
        story_repo = StoryKnowledgeRepository(tempfile.mkdtemp())
        service = StoryKnowledgeService(story_repo)
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.memory_scope_id = "scope-fail"
        for index in range(3):
            fixture.manager.public_events.append(
                _event(
                    f"evt-{index}",
                    f"Alice falsely claimed the emerald is hidden under bench {index}.",
                    turn_index=index + 1,
                    known_by=["Alice", "Bob"],
                )
            )
        service.project_after_commit(fixture, source_domain_commit_id="c1")
        index_path = story_repo.semantic_index_path(fixture.memory_scope_id)
        if index_path.exists():
            index_path.unlink()

        librarian = LibrarianService(
            retrieval_service=RetrievalService(story_knowledge_repo=story_repo)
        )
        request = KnowledgeAccessRequest(
            request_id="kar-fail",
            consumer_role="character",
            audit_reason="unit_test",
            pipeline_stage="character",
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id="round-1",
            turn_index=1,
            visibility_envelope=VisibilityEnvelope(
                viewer_role="character",
                authority_ceiling_enforced="suggestive",
                viewer_character_id="Alice",
            ),
            information_need=InformationNeed(
                focus_questions=("Where is the emerald hidden?",),
            ),
            budget_expectations=BudgetExpectations(max_bundle_entries=8, max_bundle_chars=80),
            host_allowed_information_classes=frozenset({"story_occurrence"}),
        )
        bundle = librarian.access_knowledge(request, fixture, allow_deterministic_fallback=False)
        self.assertEqual(bundle.mediation_outcome, "retrieval_failure")
        self.assertNotEqual(bundle.mediation_outcome, "no_match")


if __name__ == "__main__":
    unittest.main()
