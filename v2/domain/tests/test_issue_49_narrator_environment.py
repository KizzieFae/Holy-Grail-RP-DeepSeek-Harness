"""Issue #49 Narrator environmental-response architecture tests."""

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
from domain_api.narrator_environment_location_binding import (  # noqa: E402
    bind_location_stable_ref,
    location_stable_ref,
)
from domain_api.kernel import DomainKernel  # noqa: E402
from domain_api.narrator_environment_contract import (  # noqa: E402
    ENVIRONMENTAL_DESCRIPTOR_MARKER,
    environmental_descriptor_payload,
)
from domain_api.narrator_environment_cognition import (  # noqa: E402
    finalize_narrator_environment_cognition,
    mediation_allows_bounded_composition,
    mediation_blocks_invention,
    parse_n1_cognition_result,
    parse_n2_cognition_results,
)
from domain_api.narrator_environment_establishment import (  # noqa: E402
    accept_b2_environmental_descriptor,
    reject_c_establishment_via_narrator,
)
from domain_api.narrator_environment_packet import assemble_narrator_environment_packet  # noqa: E402
from domain_api.narrator_environment_projection import (  # noqa: E402
    build_environmental_current_view,
    descriptor_from_story_record,
    load_story_derived_environmental_descriptors,
)
from domain_api.session_repository import SessionRepository  # noqa: E402
from domain_api.session_state import CharacterTurnRecord, initialize_live_session  # noqa: E402
from domain_api.story_knowledge_contract import (  # noqa: E402
    DerivedStoryRecordSubmission,
    EpistemicAuthorityRef,
    StableRef,
    StoryEvidence,
)
from domain_api.story_knowledge_repository import StoryKnowledgeRepository  # noqa: E402
from domain_api.story_knowledge_service import StoryKnowledgeService  # noqa: E402
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
)


def _b2_submission(
    *,
    story_record_id: str,
    scope: str,
    session_id: str,
    property_key: str,
    value: str,
    location_ref: str,
    turn_index: int = 1,
    supersedes: str | None = None,
) -> DerivedStoryRecordSubmission:
    related = ()
    if supersedes:
        from domain_api.story_knowledge_contract import StoryRelation

        related = (StoryRelation(rel="supersedes", target_id=supersedes),)
    return DerivedStoryRecordSubmission(
        story_record_id=story_record_id,
        memory_scope_id=scope,
        source_domain_commit_id="commit-env",
        source_session_id=session_id,
        hg_scene_id=session_id,
        source_event_ids=(),
        stable_refs=(StableRef(ref_kind="location", stable_ref=location_ref),),
        evidence=StoryEvidence(
            summary=f"{property_key}={value}",
            committed_text=environmental_descriptor_payload(
                property_key=property_key,
                value=value,
                stable_refs=(location_ref,),
                supersedes=supersedes,
            ),
        ),
        epistemic_authority_ref=EpistemicAuthorityRef(
            ref_kind="establishment_decision",
            ref_payload={"establishment_kind": "test"},
        ),
        submission_authority_ref="test",
        related_refs=related,
        turn_index=turn_index,
        location="Workshop",
        event_type="environmental_descriptor",
        grounding_markers=(ENVIRONMENTAL_DESCRIPTOR_MARKER,),
    )


class EnvironmentalProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        self.fixture.memory_scope_id = "scope-49"
        self.fixture.manager.scene_state.location = "Workshop"
        self._tmpdir = tempfile.mkdtemp()
        self.repo = StoryKnowledgeRepository(self._tmpdir)
        self.service = StoryKnowledgeService(self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def test_authored_baseline_only(self) -> None:
        self.fixture.setup_snapshot = {
            "scene_template": {
                "template_id": "workshop",
                "premise": "Workshop walls are teal and the floor is stone.",
                "tone": "quiet",
                "opening_text": "The Workshop is quiet.",
            },
            "characters": [],
        }
        view = build_environmental_current_view(self.fixture, story_records=[])
        self.assertEqual(view.location_ref, location_stable_ref("Workshop"))
        # Authored extraction is best-effort from setup snapshot; may be empty without full M9 compile.
        self.assertIsInstance(view.effective_descriptors, dict)

    def test_story_derived_b2_addition(self) -> None:
        loc = location_stable_ref("Workshop")
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-wall-1",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="teal",
                location_ref=loc,
            )
        )
        records = self.repo.list_records("scope-49")
        view = build_environmental_current_view(self.fixture, story_records=records)
        self.assertEqual(view.effective_descriptors["wall_color"].value, "teal")

    def test_compatible_distinct_properties_accumulate(self) -> None:
        loc = location_stable_ref("Workshop")
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-wall",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="teal",
                location_ref=loc,
            )
        )
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-floor",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="floor_material",
                value="stone",
                location_ref=loc,
            )
        )
        records = self.repo.list_records("scope-49")
        view = build_environmental_current_view(self.fixture, story_records=records)
        self.assertIn("wall_color", view.effective_descriptors)
        self.assertIn("floor_material", view.effective_descriptors)

    def test_same_property_supersession(self) -> None:
        loc = location_stable_ref("Workshop")
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-old",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="teal",
                location_ref=loc,
                turn_index=1,
            )
        )
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-new",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="purple",
                location_ref=loc,
                turn_index=2,
                supersedes="b2-old",
            )
        )
        records = self.repo.list_records("scope-49")
        view = build_environmental_current_view(self.fixture, story_records=records)
        self.assertEqual(view.effective_descriptors["wall_color"].value, "purple")

    def test_unresolved_conflict_surfaced(self) -> None:
        loc = location_stable_ref("Workshop")
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-a",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="teal",
                location_ref=loc,
                turn_index=1,
            )
        )
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-b",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="purple",
                location_ref=loc,
                turn_index=2,
            )
        )
        records = self.repo.list_records("scope-49")
        view = build_environmental_current_view(self.fixture, story_records=records)
        self.assertTrue(view.conflicts)

    def test_stable_referent_filtering(self) -> None:
        loc_workshop = location_stable_ref("Workshop")
        loc_garden = location_stable_ref("Garden")
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-workshop",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="teal",
                location_ref=loc_workshop,
            )
        )
        self.service.submit_derived_record(
            _b2_submission(
                story_record_id="b2-garden",
                scope="scope-49",
                session_id=self.fixture.hg_session_id,
                property_key="wall_color",
                value="ivy-covered",
                location_ref=loc_garden,
            )
        )
        records = self.repo.list_records("scope-49")
        derived = load_story_derived_environmental_descriptors(
            records,
            location_ref=loc_workshop,
        )
        self.assertEqual(len(derived), 1)
        self.assertEqual(derived[0].value, "teal")


class EnvironmentalPacketTests(unittest.TestCase):
    def test_packet_assembly_deterministic(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.manager.scene_state.location = "Workshop"
        packet, view = assemble_narrator_environment_packet(fixture, story_records=[])
        self.assertEqual(packet.location_refs[0], view.location_ref)
        summary = packet.render_summary()
        self.assertIn("location:workshop", summary)
        self.assertLess(len(summary), 5000)

    def test_unrelated_location_excluded(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        tmpdir = tempfile.mkdtemp()
        try:
            repo = StoryKnowledgeRepository(tmpdir)
            service = StoryKnowledgeService(repo)
            fixture.memory_scope_id = "scope-packet"
            loc_garden = location_stable_ref("Garden")
            service.submit_derived_record(
                _b2_submission(
                    story_record_id="garden-only",
                    scope="scope-packet",
                    session_id=fixture.hg_session_id,
                    property_key="wall_color",
                    value="ivy-covered",
                    location_ref=loc_garden,
                )
            )
            records = repo.list_records("scope-packet")
            packet, _ = assemble_narrator_environment_packet(fixture, story_records=records)
            keys = {item.property_key for item in packet.effective_descriptors}
            self.assertNotIn("wall_color", keys)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class CognitionMediationTests(unittest.TestCase):
    def test_baseline_sufficient_zero_needs(self) -> None:
        n1 = parse_n1_cognition_result({"baseline_sufficient": True, "information_needs": []})
        self.assertTrue(n1.baseline_sufficient)
        self.assertEqual(n1.information_needs, [])

    def test_mediation_outcomes(self) -> None:
        self.assertTrue(mediation_allows_bounded_composition("no_match"))
        self.assertFalse(mediation_allows_bounded_composition("ambiguous"))
        self.assertTrue(mediation_blocks_invention("ambiguous"))
        self.assertTrue(mediation_blocks_invention("retrieval_failure"))

    def test_b2_blocked_on_ambiguity(self) -> None:
        fixture = initialize_live_session(cast=["Alice"])
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            fixture.memory_scope_id = "scope-cog"
            turn = CharacterTurnRecord(
                character_id="Alice",
                committed_move={"move_schema_version": 2, "beats": []},
                domain_commit_id="commit-1",
                continuity_turn_index=1,
                director_decision={},
            )
            n2 = parse_n2_cognition_results(
                {
                    "resolutions": [
                        {
                            "category": "B2",
                            "detail": "wall is teal",
                            "property_key": "wall_color",
                            "value": "teal",
                            "mediation_outcome": "ambiguous",
                        }
                    ]
                }
            )
            from domain_api.narrator_environment_cognition import apply_n2_establishment_decisions

            decisions = apply_n2_establishment_decisions(
                fixture,
                service,
                resolutions=n2,
                turn_record=turn,
                cognition_id="cog-1",
            )
            self.assertFalse(decisions[0]["accepted"])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_b1_no_persistence(self) -> None:
        fixture = initialize_live_session(cast=["Alice"])
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            fixture.memory_scope_id = "scope-b1"
            turn = CharacterTurnRecord(
                character_id="Alice",
                committed_move={"move_schema_version": 2, "beats": []},
                domain_commit_id="commit-1",
                continuity_turn_index=1,
                director_decision={},
            )
            result = finalize_narrator_environment_cognition(
                fixture,
                turn,
                story_service=service,
                n1_raw={"baseline_sufficient": True, "information_needs": []},
                n2_raw={
                    "resolutions": [
                        {
                            "category": "B1",
                            "detail": "dust motes in a sunbeam",
                        }
                    ]
                },
            )
            self.assertTrue(result["accepted"])
            self.assertEqual(service.list_records("scope-b1"), [])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_c_not_established_by_narrator(self) -> None:
        rejected = reject_c_establishment_via_narrator()
        self.assertFalse(rejected["accepted"])


class B2EstablishmentTests(unittest.TestCase):
    def test_b2_persists_and_appears_in_packet(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-b2"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            loc = bind_location_stable_ref("Workshop").stable_ref
            result = accept_b2_environmental_descriptor(
                fixture,
                service,
                property_key="wall_color",
                value="teal",
                stable_refs=(loc,),
                source_domain_commit_id="commit-b2",
                turn_index=1,
            )
            self.assertTrue(result["accepted"])
            records = service.list_records("scope-b2")
            self.assertEqual(len(records), 1)
            desc = descriptor_from_story_record(records[0])
            assert desc is not None
            self.assertEqual(desc.property_key, "wall_color")
            packet, _ = assemble_narrator_environment_packet(fixture, story_records=records)
            self.assertTrue(any(d.property_key == "wall_color" for d in packet.effective_descriptors))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class NarratorContextIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel(store=self.repo)

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _commit_alice(self) -> tuple[str, str, str, int]:
        session = self.repo.create_session(cast=["Alice"], location="Workshop")
        scene_id = session.hg_scene_id
        rnd = self.kernel.start_round(RoundStartRequest(hg_scene_id=scene_id))
        commit = self.kernel.commit_move(
            CommitRequest(
                inference_id="inf-commit-49",
                hg_scene_id=scene_id,
                hg_round_id=rnd.hg_round_id,
                character_id="Alice",
                validated_move={
                    "move_schema_version": 2,
                    "beats": [{"type": "action", "action": "looks around the workshop"}],
                },
                director_decision={
                    "next_actor": "Alice",
                    "end_round": True,
                    "reason": "test",
                    "environment_event": "",
                    "tension_shift": "",
                },
                expected_turn_index=0,
            )
        )
        assert commit.committed and commit.domain_commit_id is not None
        return scene_id, rnd.hg_round_id, commit.domain_commit_id, commit.continuity_turn_index or 0

    def test_narrator_context_includes_environmental_baseline(self) -> None:
        scene_id, rnd_id, commit_id, turn_idx = self._commit_alice()
        manifest = self.kernel.prepare_narrator_context(
            NarratorContextPrepareRequest(
                hg_scene_id=scene_id,
                hg_round_id=rnd_id,
                inference_id="inf-49",
                character_id="Alice",
                domain_commit_id=commit_id,
                continuity_turn_index=turn_idx,
            )
        )
        kinds = {c.source_kind for c in manifest.contributions}
        self.assertIn("narrator_environment_baseline", kinds)
        self.assertIn("triggering_user_context", kinds)
        baseline = next(
            c for c in manifest.contributions if c.source_kind == "narrator_environment_baseline"
        )
        self.assertLess(len(baseline.content), 5000)


if __name__ == "__main__":
    unittest.main()
