"""#31 S0+S1 retrieval contract and façade tests."""

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

from domain_api.character_retrieval_adapter import (  # noqa: E402
    build_character_packaging_request,
    candidate_to_authored_record,
)
from domain_api.compiled_index_provider import CompiledIndexRetrievalProvider  # noqa: E402
from domain_api.knowledge_service import KnowledgeService  # noqa: E402
from domain_api.retrieval_contract import (  # noqa: E402
    BackendRetrievalRank,
    GenerationHints,
    HardAccessConstraints,
    RetrievalAccessRequest,
    RetrievalCandidate,
    RetrievalCandidatePayload,
    ResponseBudget,
    validate_retrieval_access_request,
)
from domain_api.retrieval_selection import (  # noqa: E402
    MAX_GLOBAL_RETRIEVAL_CHARS,
    MAX_GLOBAL_RETRIEVAL_ITEMS,
    select_retrieval_records,
)
from domain_api.retrieval_service import RetrievalService  # noqa: E402
from domain_api.scope_knowledge_repository import (  # noqa: E402
    LEARNED_WORLD_KNOWLEDGE,
    ScopeKnowledgeRecord,
    ScopeKnowledgeRepository,
)
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_state import initialize_live_session, RoundFixture  # noqa: E402
from domain.paths import holy_grail_data_dir  # noqa: E402


class RetrievalContractTests(unittest.TestCase):
    def test_hard_access_and_generation_hints_are_distinct_layers(self) -> None:
        hard = HardAccessConstraints(
            viewer_character_id="Alice",
            subject_character_file_id="alice",
            allowed_information_classes=frozenset({"authored_static"}),
            prohibited_information_classes=frozenset({"compiled_index"}),
        )
        hints = GenerationHints(
            query_terms=("secret",),
            entity_anchors=("alice",),
            recall_mode="focused",
            class_recall_budgets={"authored_static": 2},
        )
        request = RetrievalAccessRequest(
            request_id="req-1",
            consumer_role="librarian",
            hg_scene_id="scene-1",
            hg_round_id="round-1",
            turn_index=0,
            hard_access=hard,
            generation_hints=hints,
        )
        validate_retrieval_access_request(request)
        self.assertNotEqual(request.hard_access, request.generation_hints)
        self.assertIn("authored_static", request.hard_access.allowed_information_classes)
        self.assertEqual(request.generation_hints.query_terms, ("secret",))

    def test_validate_rejects_unknown_information_class(self) -> None:
        request = RetrievalAccessRequest(
            request_id="req-bad",
            consumer_role="librarian",
            hg_scene_id="scene-1",
            hg_round_id="round-1",
            turn_index=0,
            hard_access=HardAccessConstraints(
                allowed_information_classes=frozenset({"not_a_real_class"}),
            ),
        )
        with self.assertRaises(ValueError):
            validate_retrieval_access_request(request)

    def test_candidate_consumer_dict_preserves_class_and_rank_not_relevance(self) -> None:
        candidate = RetrievalCandidate(
            candidate_id="cand-1",
            information_class="compiled_index",
            payload=RetrievalCandidatePayload(content="indexed lore"),
            authority_class="suggestive",
            visibility="public",
            provenance={
                "knowledge_lane": "authored_character_knowledge",
                "source_kind": "compiled_index",
            },
            backend_retrieval_rank=BackendRetrievalRank(
                retrieval_provider_id="compiled-index-v3",
                rank_metric="source_index",
                rank_value=3,
            ),
            host_internal_metadata={"debug": True},
        )
        exported = candidate.consumer_dict()
        self.assertEqual(exported["information_class"], "compiled_index")
        self.assertEqual(exported["backend_retrieval_rank"]["rank_metric"], "source_index")
        self.assertNotIn("semantic_relevance", exported)
        self.assertNotIn("librarian_relevance", exported)
        self.assertNotIn("host_internal_metadata", exported)


class RetrievalServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.scope_repo = ScopeKnowledgeRepository(self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _fixture_with_snapshot(self) -> tuple[object, RetrievalService]:
        fixture = initialize_live_session(cast=["Alice", "Bob"])
        fixture.setup_snapshot = {
            "scene_template_id": "test_template",
            "scene_template": {
                "premise": "A test premise for scene reference lane.",
                "tone": "tense",
            },
            "character_cards": {
                "alice": {
                    "lore_facts": ["Alice knows the hidden passage.", "Alice trusts Bob."],
                },
                "bob": {
                    "lore_facts": ["Bob guards the gate."],
                },
            },
        }
        fixture.memory_scope_id = "scope-test"
        fixture.rounds.append(
            RoundFixture(
                hg_round_id="round-1",
                hg_scene_id=fixture.hg_scene_id,
                turn_index=0,
            )
        )
        service = RetrievalService(scope_repo=self.scope_repo)
        return fixture, service

    def test_hard_access_excludes_other_character_scope(self) -> None:
        fixture, service = self._fixture_with_snapshot()
        self.scope_repo.append_records(
            [
                ScopeKnowledgeRecord(
                    knowledge_id="world-1",
                    scope_id=fixture.memory_scope_id,
                    knowledge_kind=LEARNED_WORLD_KNOWLEDGE,
                    content="Global world fact.",
                    visibility="scope_global",
                    source_kind="continuity_promotion",
                    source_continuity_anchor_id="anchor-missing",
                    provenance={"knowledge_lane": LEARNED_WORLD_KNOWLEDGE},
                    created_at="2026-01-01T00:00:00+00:00",
                ),
                ScopeKnowledgeRecord(
                    knowledge_id="world-2",
                    scope_id=fixture.memory_scope_id,
                    knowledge_kind=LEARNED_WORLD_KNOWLEDGE,
                    content="Alice-only fact.",
                    visibility="character_scoped",
                    subject_character_file_id="alice",
                    source_kind="continuity_promotion",
                    source_continuity_anchor_id="anchor-missing",
                    provenance={"knowledge_lane": LEARNED_WORLD_KNOWLEDGE},
                    created_at="2026-01-02T00:00:00+00:00",
                ),
            ]
        )
        request = RetrievalAccessRequest(
            request_id="req-scope",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_session_id,
            hg_round_id="round-1",
            turn_index=0,
            memory_scope_id=fixture.memory_scope_id,
            hard_access=HardAccessConstraints(
                viewer_character_id="Bob",
                subject_character_file_id="bob",
                allowed_information_classes=frozenset(
                    {"authored_static", "promoted_learned_world"}
                ),
            ),
            generation_hints=GenerationHints(class_recall_budgets={"promoted_learned_world": 8}),
            response_budget=ResponseBudget(max_candidates=32, max_total_chars=16000),
        )
        response = service.retrieve(request, fixture)
        world_contents = {
            c.payload.content
            for c in response.candidates
            if c.information_class == "promoted_learned_world"
        }
        self.assertIn("Global world fact.", world_contents)
        self.assertNotIn("Alice-only fact.", world_contents)
        self.assertGreaterEqual(response.diagnostics.hard_access_rejected, 1)

    def test_generation_hints_do_not_override_hard_prohibition(self) -> None:
        fixture, service = self._fixture_with_snapshot()
        request = RetrievalAccessRequest(
            request_id="req-hints",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_session_id,
            hg_round_id="round-1",
            turn_index=0,
            hard_access=HardAccessConstraints(
                viewer_character_id="Alice",
                subject_character_file_id="alice",
                session_template_id="test_template",
                allowed_information_classes=frozenset({"authored_static"}),
                prohibited_information_classes=frozenset({"compiled_index"}),
            ),
            generation_hints=GenerationHints(
                query_terms=("compiled", "index"),
                source_preferences=("compiled_index",),
                class_recall_budgets={"compiled_index": 99},
            ),
            response_budget=ResponseBudget(max_candidates=32, max_total_chars=16000),
        )
        response = service.retrieve(request, fixture)
        classes = {c.information_class for c in response.candidates}
        self.assertIn("authored_static", classes)
        self.assertNotIn("compiled_index", classes)

    def test_response_budget_is_deterministic(self) -> None:
        fixture, service = self._fixture_with_snapshot()
        request = RetrievalAccessRequest(
            request_id="req-budget",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_session_id,
            hg_round_id="round-1",
            turn_index=0,
            hard_access=HardAccessConstraints(
                viewer_character_id="Alice",
                subject_character_file_id="alice",
                session_template_id="test_template",
                allowed_information_classes=frozenset({"authored_static"}),
            ),
            response_budget=ResponseBudget(max_candidates=1, max_total_chars=40),
        )
        response = service.retrieve(request, fixture)
        self.assertEqual(len(response.candidates), 1)
        self.assertGreater(response.diagnostics.budget_exhausted, 0)

    def test_empty_results_are_valid(self) -> None:
        fixture = initialize_live_session()
        fixture.rounds.append(
            RoundFixture(
                hg_round_id="round-1",
                hg_scene_id=fixture.hg_scene_id,
                turn_index=0,
            )
        )
        service = RetrievalService(scope_repo=self.scope_repo)
        request = RetrievalAccessRequest(
            request_id="req-empty",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_session_id,
            hg_round_id="round-1",
            turn_index=0,
            hard_access=HardAccessConstraints(
                allowed_information_classes=frozenset({"authored_static"}),
            ),
        )
        response = service.retrieve(request, fixture)
        self.assertEqual(response.candidates, ())
        self.assertEqual(response.degradation_level, "none")

    def test_degraded_index_provider_reports_partial(self) -> None:
        fixture, _ = self._fixture_with_snapshot()
        bad_path = Path(self._tmpdir) / "bad-index.json"
        bad_path.write_text("{not json", encoding="utf-8")
        service = RetrievalService(
            scope_repo=self.scope_repo,
            retrieval_provider=CompiledIndexRetrievalProvider(bad_path),
        )
        request = RetrievalAccessRequest(
            request_id="req-degraded",
            consumer_role="librarian",
            hg_scene_id=fixture.hg_session_id,
            hg_round_id="round-1",
            turn_index=0,
            hard_access=HardAccessConstraints(
                viewer_character_id="Alice",
                subject_character_file_id="alice",
                allowed_information_classes=frozenset({"authored_static", "compiled_index"}),
            ),
        )
        response = service.retrieve(request, fixture)
        self.assertEqual(response.degradation_level, "partial")
        statuses = {item.status for item in response.diagnostics.provider_status}
        self.assertIn("degraded", statuses)


class CharacterCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_character_packaging_caps_remain_on_legacy_selection(self) -> None:
        fixture = initialize_live_session(cast=["Alice"])
        fixture.setup_snapshot = {
            "scene_template_id": "test_template",
            "scene_template": {
                "premise": "Premise one.",
                "tone": "calm",
                "opening_text": "Opening line.",
            },
            "character_cards": {
                "alice": {
                    "lore_facts": [f"Fact {i}" for i in range(10)],
                },
            },
        }
        fixture.character_file_ids = {"Alice": "alice"}
        fixture.rounds.append(
            RoundFixture(
                hg_round_id="round-1",
                hg_scene_id=fixture.hg_scene_id,
                turn_index=0,
            )
        )
        request = build_character_packaging_request(fixture, character_id="Alice")
        response = RetrievalService(scope_repo=self.repo.knowledge_service.scope_repo).retrieve(
            request, fixture
        )
        authored = [
            candidate_to_authored_record(candidate)
            for candidate in response.candidates
            if candidate.information_class in {"authored_static", "compiled_index"}
        ]
        authored = [record for record in authored if record is not None]
        self.assertGreater(len(authored), MAX_GLOBAL_RETRIEVAL_ITEMS)
        character_records, scene_records = select_retrieval_records(
            authored,
            character_file_id="alice",
            session_template_id="test_template",
        )
        selected_count = len(character_records) + len(scene_records)
        self.assertLessEqual(selected_count, MAX_GLOBAL_RETRIEVAL_ITEMS)
        total_chars = sum(len(r.content) for r in character_records + scene_records)
        self.assertLessEqual(total_chars, MAX_GLOBAL_RETRIEVAL_CHARS)

    def test_knowledge_service_character_path_still_projects(self) -> None:
        pilot_index = (
            holy_grail_data_dir()
            / "retrieval"
            / "compiled"
            / "operational_pilot_v3.json"
        )
        self.repo.knowledge_service = KnowledgeService(
            scope_repo=self.repo.knowledge_service.scope_repo,
            retrieval_provider=CompiledIndexRetrievalProvider(pilot_index),
        )
        info = self.repo.create_session(
            characters=["kizzie", "willow"],
            scene_template_id="celina_apartment_recovery_watch",
            role_assignments={
                "kizzie": "recovering_demi_human",
                "willow": "protector",
            },
        )
        fixture = self.repo.require(info.hg_session_id)
        fixture.rounds.append(
            RoundFixture(
                hg_round_id="round-compat",
                hg_scene_id=fixture.hg_scene_id,
                turn_index=0,
            )
        )
        projections = self.repo.knowledge_service.project_context(fixture, character_id="Kizzie")
        lanes = {item[0] for item in projections}
        self.assertIn("authored_character_knowledge", lanes)
        self.assertIn("scene_reference", lanes)


if __name__ == "__main__":
    unittest.main()
