"""#32 S3a Storyteller cognition tests."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_V2 = _ROOT / "v2"
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))

from domain_api.librarian_contract import (  # noqa: E402
    LIBRARIAN_MEDIATION_RESULT_SCHEMA,
    InformationNeed,
    KnowledgeAccessRequest,
    QuestionOutcome,
    RequestSatisfactionSummary,
    VisibilityEnvelope,
    validate_knowledge_access_request,
)
from domain_api.librarian_mediation_catalog import build_mediation_working_set  # noqa: E402
from domain_api.librarian_service import LibrarianService, MediationAssembly  # noqa: E402
from domain_api.retrieval_contract import RetrievalCandidate, RetrievalCandidatePayload  # noqa: E402
from domain_api.retrieval_service import RetrievalService  # noqa: E402
from domain_api.scope_knowledge_repository import ScopeKnowledgeRepository  # noqa: E402
from domain_api.session_state import RoundFixture, initialize_live_session  # noqa: E402
from domain_api.storyteller_contract import (  # noqa: E402
    STORYTELLER_ASSESSMENT_SCHEMA,
    STORYTELLER_ORIENTATION_SCHEMA,
    StorytellerOrientationAssessment,
    build_storyteller_advisory_package,
    invalidate_storyteller_package,
    orientation_to_knowledge_access_request,
    parse_storyteller_assessment,
    parse_storyteller_orientation,
    validate_storyteller_payload,
)
from domain_api.storyteller_service import StorytellerService  # noqa: E402


def _candidate(candidate_id: str, content: str) -> RetrievalCandidate:
    return RetrievalCandidate(
        candidate_id=candidate_id,
        information_class="authored_static",
        payload=RetrievalCandidatePayload(content=content),
        authority_class="suggestive",
        visibility="public",
    )


def _valid_orientation(**overrides: object) -> dict:
    payload = {
        "schema": STORYTELLER_ORIENTATION_SCHEMA,
        "orientation_id": "orient-1",
        "hg_round_id": "round-1",
        "turn_index": 0,
        "trigger": "round_start",
        "information_gaps": (
            "What tensions are active in the scene?",
            "Which relationships are under strain?",
        ),
        "temporal_focus": "current",
        "breadth_preference": "broad",
    }
    payload.update(overrides)
    return payload


def _valid_assessment(**overrides: object) -> dict:
    payload = {
        "schema": STORYTELLER_ASSESSMENT_SCHEMA,
        "assessment_id": "assess-1",
        "observations": [
            {
                "text": "The broken trust between allies is narratively central.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
                "confidence": "likely",
            }
        ],
        "active_tensions": [
            {
                "label": "Betrayal strain",
                "interpretive_note": "Unresolved betrayal creates pressure without forcing confrontation.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "narrative_priorities": [
            {
                "focus": "Trust fracture",
                "why_it_matters": "Actors may attend to whether reconciliation or avoidance becomes meaningful.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "progression_opportunities": [
            {
                "opportunity_label": "Confrontation or avoidance",
                "narrative_hook": "The betrayal creates an opportunity for either path to become meaningful.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "unresolved_threads": [
            {
                "thread_label": "Broken treaty seal",
                "neglect_risk": "May fade if not referenced again.",
                "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
            }
        ],
        "uncertainty": [
            {
                "topic": "Hidden passage danger",
                "reason": "Bundle does not fully establish current risk level.",
                "confidence": "speculative",
            }
        ],
        "information_gaps": [
            {"question": "Who knows about the passage now?", "blocking_judgment": False}
        ],
        "evidence_refs": [{"ref_kind": "bundle_entry", "stable_ref": "entry-1"}],
    }
    payload.update(overrides)
    return payload


class StorytellerContractTests(unittest.TestCase):
    def test_orientation_maps_to_valid_kar(self) -> None:
        orientation, error = parse_storyteller_orientation(_valid_orientation())
        assert orientation is not None
        assert error is None
        request = orientation_to_knowledge_access_request(
            orientation,
            hg_scene_id="scene-1",
            request_id="req-1",
            visibility_envelope={
                "viewer_role": "orchestration",
                "authority_ceiling_enforced": "derived",
            },
            host_allowed_information_classes=frozenset({"authored_static"}),
        )
        self.assertEqual(request.consumer_role, "storyteller")
        self.assertEqual(request.pipeline_stage, "host_default")
        validate_knowledge_access_request(request)

    def test_orientation_rejects_prohibited_fields(self) -> None:
        orientation, error = parse_storyteller_orientation(
            _valid_orientation(next_actor="Alice")
        )
        self.assertIsNone(orientation)
        self.assertIn("prohibited_fields", error or "")

    def test_orientation_requires_information_gaps(self) -> None:
        orientation, error = parse_storyteller_orientation(_valid_orientation(information_gaps=[]))
        self.assertIsNone(orientation)
        self.assertEqual(error, "information_gaps_required")

    def test_assessment_rejects_railroading_fields(self) -> None:
        parsed, error = parse_storyteller_assessment(
            _valid_assessment(progression_opportunities=[{"required_action": "Alice must confront Bob"}])
        )
        self.assertIsNone(parsed)
        self.assertIn("prohibited_fields", error or "")

    def test_assessment_rejects_next_actor(self) -> None:
        ok, violations = validate_storyteller_payload({"next_actor": "Alice"})
        self.assertFalse(ok)
        self.assertTrue(violations)

    def test_assessment_rejects_dialogue_and_structured_move(self) -> None:
        for field in ("dialogue", "structured_move", "continuity_mutation"):
            ok, violations = validate_storyteller_payload({field: "bad"})
            self.assertFalse(ok, field)
            self.assertTrue(violations)

    def test_invalidated_package_not_valid_for_consumption(self) -> None:
        orientation, _ = parse_storyteller_orientation(_valid_orientation())
        assert orientation is not None
        assessment, _ = parse_storyteller_assessment(_valid_assessment())
        assert assessment is not None
        package = build_storyteller_advisory_package(
            assessment=assessment,
            orientation=orientation,
            hg_scene_id="scene-1",
            bundle_refs=__import__(
                "domain_api.storyteller_contract", fromlist=["StorytellerBundleRefs"]
            ).StorytellerBundleRefs(
                primary_request_id="req-1",
                primary_bundle_id="bundle-1",
            ),
            authoritative_snapshot_id="snap-1",
            audit=__import__(
                "domain_api.storyteller_contract", fromlist=["StorytellerAuditRecord"]
            ).StorytellerAuditRecord(),
        )
        self.assertTrue(package.validity.is_valid)
        invalidated = invalidate_storyteller_package(package, reason="authoritative_commit")
        self.assertFalse(invalidated.validity.is_valid)
        self.assertEqual(invalidated.validity.invalidation_reason, "authoritative_commit")


class StorytellerServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        scope_repo = ScopeKnowledgeRepository(self._tmpdir)
        librarian = LibrarianService(RetrievalService(scope_repo=scope_repo))
        self.service = StorytellerService(librarian_service=librarian)
        self.librarian = librarian

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

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

    def _bundle(self, fixture, request: KnowledgeAccessRequest):
        candidates = [_candidate("c1", "Alice learned Bob broke the treaty seal.")]
        original_assemble = self.librarian.assemble_mediation_inputs

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

        self.librarian.assemble_mediation_inputs = _stub_assemble  # type: ignore[method-assign]
        try:
            return self.librarian.access_knowledge(
                request,
                fixture,
                mediation_result={
                    "schema": LIBRARIAN_MEDIATION_RESULT_SCHEMA,
                    "selected_items": [
                        {
                            "source_id": "lmi:cand:c1",
                            "relevance_rank": 1,
                            "answers_focus_questions": list(request.information_need.focus_questions),
                        }
                    ],
                },
            )
        finally:
            self.librarian.assemble_mediation_inputs = original_assemble  # type: ignore[method-assign]

    def test_prepare_orientation_context_has_instruction_and_no_backend_terms(self) -> None:
        fixture = self._fixture()
        rnd = fixture.rounds[-1]
        prepared = self.service.prepare_orientation_context(fixture, rnd, inference_id="inf-1")
        contents = " ".join(item["content"] for item in prepared["contributions"])
        self.assertIn("STORYTELLER ORIENTATION", contents)
        self.assertNotIn("candidate_id", contents.lower())
        self.assertNotIn("semantic_relevance_score", contents.lower())

    def test_finalize_orientation_produces_storyteller_kar(self) -> None:
        fixture = self._fixture()
        rnd = fixture.rounds[-1]
        finalized = self.service.finalize_orientation(
            fixture,
            rnd,
            inference_id="inf-1",
            orientation_result=_valid_orientation(hg_round_id=rnd.hg_round_id),
        )
        self.assertTrue(finalized["accepted"])
        kar = finalized["knowledge_access_request"]
        self.assertEqual(kar["consumer_role"], "storyteller")
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

    def test_end_to_end_advisory_package(self) -> None:
        fixture = self._fixture()
        rnd = fixture.rounds[-1]
        orientation_result = self.service.finalize_orientation(
            fixture,
            rnd,
            inference_id="inf-1",
            orientation_result=_valid_orientation(hg_round_id=rnd.hg_round_id),
        )
        assert orientation_result["accepted"]
        kar_dict = orientation_result["knowledge_access_request"]
        assert kar_dict is not None
        request = KnowledgeAccessRequest(
            request_id=kar_dict["request_id"],
            consumer_role="storyteller",
            audit_reason=kar_dict["audit_reason"],
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id=kar_dict["hg_round_id"],
            turn_index=kar_dict["turn_index"],
            pipeline_stage="host_default",
            visibility_envelope=VisibilityEnvelope(
                viewer_role="orchestration",
                authority_ceiling_enforced="derived",
                session_template_id=kar_dict["visibility_envelope"].get("session_template_id"),
            ),
            information_need=InformationNeed(
                focus_questions=tuple(kar_dict["information_need"]["focus_questions"]),
            ),
            host_allowed_information_classes=frozenset(kar_dict["host_allowed_information_classes"]),
        )
        bundle = self._bundle(fixture, request)
        orientation = StorytellerOrientationAssessment(
            orientation_id=orientation_result["orientation"]["orientation_id"],
            hg_round_id=rnd.hg_round_id,
            turn_index=0,
            trigger="round_start",
            information_gaps=tuple(kar_dict["information_need"]["focus_questions"]),
        )
        prepared = self.service.prepare_assessment_context(orientation, bundle, inference_id="inf-1")
        self.assertIn("librarian_bundle_digest", json.dumps(prepared))
        finalized = self.service.finalize_assessment(
            fixture,
            rnd,
            orientation=orientation,
            bundle=bundle,
            assessment_result=_valid_assessment(),
            orientation_inference_id="inf-1-orient",
            assessment_inference_id="inf-1-assess",
        )
        self.assertTrue(finalized["accepted"])
        package = finalized["package"]
        assert package is not None
        self.assertEqual(package["schema"], "hg_storyteller_advisory_package_v1")
        self.assertTrue(package["validity"]["is_valid"])
        self.assertEqual(package["bundle_refs"]["primary_bundle_id"], bundle.bundle_id)
        self.assertTrue(package["observations"])
        self.assertTrue(package["progression_opportunities"])
        self.assertNotIn("required_action", json.dumps(package))

    def test_malformed_assessment_rejected(self) -> None:
        fixture = self._fixture()
        rnd = fixture.rounds[-1]
        orientation = StorytellerOrientationAssessment(
            orientation_id="orient-1",
            hg_round_id=rnd.hg_round_id,
            turn_index=0,
            trigger="round_start",
            information_gaps=("Why?",),
        )
        bundle = self._bundle(
            fixture,
            KnowledgeAccessRequest(
                request_id="req-1",
                consumer_role="storyteller",
                audit_reason="test",
                hg_scene_id=fixture.hg_scene_id,
                hg_round_id=rnd.hg_round_id,
                turn_index=0,
                pipeline_stage="host_default",
                visibility_envelope=VisibilityEnvelope(
                    viewer_role="orchestration",
                    authority_ceiling_enforced="derived",
                ),
                information_need=InformationNeed(focus_questions=("Why?",)),
            ),
        )
        finalized = self.service.finalize_assessment(
            fixture,
            rnd,
            orientation=orientation,
            bundle=bundle,
            assessment_result={"schema": STORYTELLER_ASSESSMENT_SCHEMA, "next_actor": "Alice"},
            orientation_inference_id="inf-1-orient",
            assessment_inference_id="inf-1-assess",
        )
        self.assertFalse(finalized["accepted"])
        self.assertIsNone(finalized["package"])

    def test_follow_up_request_bounded(self) -> None:
        fixture = self._fixture()
        rnd = fixture.rounds[-1]
        orientation = StorytellerOrientationAssessment(
            orientation_id="orient-1",
            hg_round_id=rnd.hg_round_id,
            turn_index=0,
            trigger="round_start",
            information_gaps=("Why?", "How?"),
        )
        request = KnowledgeAccessRequest(
            request_id="req-primary",
            consumer_role="storyteller",
            audit_reason="test",
            hg_scene_id=fixture.hg_scene_id,
            hg_round_id=rnd.hg_round_id,
            turn_index=0,
            pipeline_stage="host_default",
            visibility_envelope=VisibilityEnvelope(
                viewer_role="orchestration",
                authority_ceiling_enforced="derived",
            ),
            information_need=InformationNeed(focus_questions=("Why?", "How?")),
        )
        bundle = self._bundle(
            fixture,
            request,
        )
        bundle = replace(
            bundle,
            satisfaction=RequestSatisfactionSummary(
                focus_questions=(
                    QuestionOutcome(question="Why?", status="answered"),
                    QuestionOutcome(question="How?", status="unanswered"),
                )
            ),
        )
        follow_up = self.service.maybe_follow_up_request(
            fixture,
            rnd,
            orientation=orientation,
            bundle=bundle,
            primary_request_id="req-primary",
            inference_id="inf-1",
        )
        self.assertIsNotNone(follow_up)
        self.assertEqual(follow_up["parent_request_id"], "req-primary")
        self.assertEqual(follow_up["consumer_role"], "storyteller")
        self.assertLessEqual(len(follow_up["information_need"]["focus_questions"]), 3)


if __name__ == "__main__":
    unittest.main()
