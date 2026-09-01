"""Issue #49 Narrator environmental-response architecture tests."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

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
from domain_api.narrator_environment_authority import (  # noqa: E402
    NarratorEnvironmentalB2Proposal,
    evaluate_host_environmental_b2_establishment,
)
from domain_api.narrator_environment_cognition import (  # noqa: E402
    extract_triggering_user_context,
    finalize_narrator_environment_cognition,
    mediation_allows_bounded_composition,
    mediation_blocks_invention,
    parse_n1_cognition_result,
    parse_n2_cognition_results,
    record_environment_cognition_failure,
)
from domain_api.narrator_environment_establishment import (  # noqa: E402
    accept_b2_environmental_descriptor,
    persist_host_accepted_b2_environmental_descriptor,
    reject_c_establishment_via_narrator,
)
from domain_api.narrator_environment_packet import assemble_narrator_environment_packet  # noqa: E402
from domain_api.narrator_environment_projection import (  # noqa: E402
    build_environmental_current_view,
    descriptor_from_story_record,
    load_authored_environmental_descriptors,
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
from domain_api.story_knowledge_epistemic import (  # noqa: E402
    resolve_epistemic_authority_ref,
    story_record_epistemically_eligible,
)
from domain_api.contract import (  # noqa: E402
    CommitRequest,
    NarratorContextPrepareRequest,
    RoundStartRequest,
)


def _host_b2_decision(
    *,
    cognition_id: str = "cog-test",
    need_id: str | None = "need-1",
    property_key: str = "wall_color",
    value: str = "teal",
    stable_refs: tuple[str, ...] = ("location:workshop",),
    mediation_outcome: str = "no_match",
):
    proposal = NarratorEnvironmentalB2Proposal(
        cognition_id=cognition_id,
        need_id=need_id,
        property_key=property_key,
        value=value,
        stable_refs=stable_refs,
        mediation_outcome=mediation_outcome,
    )
    return evaluate_host_environmental_b2_establishment(proposal)


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

    def test_load_authored_environmental_descriptors_ayame_snapshot_does_not_raise(self) -> None:
        """Regression #73: load_authored must use dedupe key when recording seen entries."""
        template_path = _ROOT / "data" / "scene_templates" / "ayame_household_entry_evaluation.json"
        template = json.loads(template_path.read_text(encoding="utf-8"))
        self.fixture.setup_snapshot = {
            "scene_template_id": "ayame_household_entry_evaluation",
            "scene_template": template,
            "character_cards": {},
        }
        loc = location_stable_ref("Scene")
        descriptors = load_authored_environmental_descriptors(self.fixture, location_ref=loc)
        self.assertIsInstance(descriptors, list)

    def test_load_authored_environmental_descriptors_skips_duplicate_dedupe_keys(self) -> None:
        from domain_api.authored_knowledge import AuthoredKnowledgeRecord

        loc = location_stable_ref("Scene")
        record = AuthoredKnowledgeRecord(
            knowledge_id="auth-env-dedupe-1",
            knowledge_kind="scene_setup_fact",
            content="Scene foyer is polished marble for household evaluation.",
            authority_class="authored",
            visibility="template_participants",
            subject_character_file_id=None,
            source_kind="scene_template",
            source_asset_id="ayame_household_entry_evaluation",
            provenance={"knowledge_lane": "scene_reference"},
        )
        self.fixture.setup_snapshot = {"scene_template_id": "test", "scene_template": {}}
        with patch(
            "domain_api.narrator_environment_projection.compile_authored_records_from_snapshot",
            return_value=[record, record],
        ):
            descriptors = load_authored_environmental_descriptors(self.fixture, location_ref=loc)
        self.assertEqual(len(descriptors), 1)

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
        self.assertTrue(mediation_allows_bounded_composition("match"))
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
            self.assertIn("blocked_by_mediation", decisions[0]["reason"])
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
    def test_b2_persists_after_host_authority_acceptance(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-b2"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            loc = bind_location_stable_ref("Workshop").stable_ref
            decision = _host_b2_decision(stable_refs=(loc,))
            self.assertTrue(decision.authorized)
            result = persist_host_accepted_b2_environmental_descriptor(
                fixture,
                service,
                establishment_decision=decision,
                property_key="wall_color",
                value="teal",
                stable_refs=(loc,),
                source_domain_commit_id="commit-b2",
                turn_index=1,
                cognition_id="cog-b2",
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

    def test_n2_b2_self_classification_without_host_decision_does_not_persist(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-no-host"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            loc = bind_location_stable_ref("Workshop").stable_ref
            rejected = evaluate_host_environmental_b2_establishment(
                NarratorEnvironmentalB2Proposal(
                    cognition_id="cog-1",
                    need_id="need-1",
                    property_key="wall_color",
                    value="teal",
                    stable_refs=(loc,),
                    mediation_outcome="retrieval_failure",
                )
            )
            self.assertFalse(rejected.authorized)
            result = persist_host_accepted_b2_environmental_descriptor(
                fixture,
                service,
                establishment_decision=rejected,
                property_key="wall_color",
                value="teal",
                stable_refs=(loc,),
                source_domain_commit_id="commit-1",
                turn_index=1,
            )
            self.assertFalse(result["accepted"])
            self.assertEqual(service.list_records("scope-no-host"), [])
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class B2AuthorityMediationTests(unittest.TestCase):
    def test_match_may_authorize_b2_when_insufficient(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-match"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            turn = CharacterTurnRecord(
                character_id="Alice",
                committed_move={"move_schema_version": 2, "beats": []},
                domain_commit_id="commit-match",
                continuity_turn_index=1,
                director_decision={},
            )
            from domain_api.narrator_environment_cognition import apply_n2_establishment_decisions

            loc = bind_location_stable_ref("Workshop").stable_ref
            n2 = parse_n2_cognition_results(
                {
                    "resolutions": [
                        {
                            "category": "B2",
                            "detail": "bounded size detail",
                            "property_key": "parcel_size",
                            "value": "forearm-length",
                            "stable_refs": [loc],
                            "mediation_outcome": "match",
                            "response_sufficient": False,
                        }
                    ]
                }
            )
            decisions = apply_n2_establishment_decisions(
                fixture, service, resolutions=n2, turn_record=turn, cognition_id="cog-match"
            )
            self.assertTrue(decisions[0]["accepted"])
            self.assertEqual(len(service.list_records("scope-match")), 1)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_match_may_reach_host_and_persist(self) -> None:
        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        fixture.memory_scope_id = "scope-nomatch"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            turn = CharacterTurnRecord(
                character_id="Alice",
                committed_move={"move_schema_version": 2, "beats": []},
                domain_commit_id="commit-nm",
                continuity_turn_index=1,
                director_decision={},
            )
            from domain_api.narrator_environment_cognition import apply_n2_establishment_decisions

            n2 = parse_n2_cognition_results(
                {
                    "resolutions": [
                        {
                            "category": "B2",
                            "detail": "teal walls",
                            "property_key": "wall_color",
                            "value": "teal",
                            "stable_refs": ["location:workshop"],
                            "mediation_outcome": "no_match",
                        }
                    ]
                }
            )
            decisions = apply_n2_establishment_decisions(
                fixture, service, resolutions=n2, turn_record=turn, cognition_id="cog-nm"
            )
            self.assertTrue(decisions[0]["accepted"])
            self.assertTrue(decisions[0]["authority_decision"]["authorized"])
            self.assertEqual(len(service.list_records("scope-nomatch")), 1)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_mediation_failure_modes_block_b2(self) -> None:
        for outcome in ("ambiguous", "forbidden", "retrieval_failure", "mediation_failure", None):
            with self.subTest(outcome=outcome):
                fixture = initialize_live_session(cast=["Alice"])
                fixture.memory_scope_id = f"scope-{outcome}"
                tmpdir = tempfile.mkdtemp()
                try:
                    service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
                    turn = CharacterTurnRecord(
                        character_id="Alice",
                        committed_move={"move_schema_version": 2, "beats": []},
                        domain_commit_id="commit-x",
                        continuity_turn_index=1,
                        director_decision={},
                    )
                    from domain_api.narrator_environment_cognition import (
                        apply_n2_establishment_decisions,
                    )

                    n2 = parse_n2_cognition_results(
                        {
                            "resolutions": [
                                {
                                    "category": "B2",
                                    "property_key": "wall_color",
                                    "value": "teal",
                                    "mediation_outcome": outcome,
                                }
                            ]
                        }
                    )
                    decisions = apply_n2_establishment_decisions(
                        fixture, service, resolutions=n2, turn_record=turn, cognition_id="cog-x"
                    )
                    self.assertFalse(decisions[0]["accepted"])
                    self.assertEqual(service.list_records(f"scope-{outcome}"), [])
                finally:
                    shutil.rmtree(tmpdir, ignore_errors=True)


class B2EpistemicTests(unittest.TestCase):
    def test_accepted_b2_orchestration_only_not_auto_character_knowledge(self) -> None:
        fixture = initialize_live_session(cast=["Alice", "Bob"], location="Workshop")
        fixture.memory_scope_id = "scope-epi"
        tmpdir = tempfile.mkdtemp()
        try:
            service = StoryKnowledgeService(StoryKnowledgeRepository(tmpdir))
            loc = bind_location_stable_ref("Workshop").stable_ref
            decision = _host_b2_decision(stable_refs=(loc,))
            persist_host_accepted_b2_environmental_descriptor(
                fixture,
                service,
                establishment_decision=decision,
                property_key="wall_color",
                value="teal",
                stable_refs=(loc,),
                source_domain_commit_id="commit-epi",
                turn_index=1,
            )
            record = service.list_records("scope-epi")[0]
            assert record.epistemic_authority_ref is not None
            self.assertTrue(
                resolve_epistemic_authority_ref(
                    fixture,
                    record.epistemic_authority_ref,
                    viewer_character_id=None,
                    viewer_role="narrator",
                )
            )
            self.assertFalse(
                story_record_epistemically_eligible(
                    fixture,
                    record,
                    viewer_character_id="Alice",
                    viewer_role="character",
                )
            )
            self.assertFalse(
                story_record_epistemically_eligible(
                    fixture,
                    record,
                    viewer_character_id="Bob",
                    viewer_role="character",
                )
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


class TriggeringUserCognitionTests(unittest.TestCase):
    def test_triggering_user_reaches_cognition_when_character_omits_environment(self) -> None:
        from continuity_state_occurrence_evidence import (  # noqa: E402
            OccurrenceContribution,
            OccurrenceEvidence,
            TriggeringUser,
        )

        fixture = initialize_live_session(cast=["Alice"], location="Workshop")
        commit_id = "commit-user-env"
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-user-1",
                timestamp=datetime.now(timezone.utc),
                event_type="action",
                participants=["Alice"],
                summary="Alice shifts the heavy crate.",
                turn_index=1,
                known_by=["Alice"],
                occurrence_evidence=OccurrenceEvidence(
                    contributions=(
                        OccurrenceContribution(
                            contribution_kind="character:action",
                            producer="character",
                            content="Alice grunts and adjusts her stance.",
                        ),
                    ),
                    triggering_user=TriggeringUser(
                        entry_id="u-1",
                        speaker="Player",
                        content="I push the crate against the wall.",
                    ),
                ),
            )
        )
        turn = CharacterTurnRecord(
            character_id="Alice",
            committed_move={
                "move_schema_version": 2,
                "beats": [{"type": "action", "action": "grunts and adjusts stance"}],
            },
            domain_commit_id=commit_id,
            continuity_turn_index=1,
            director_decision={},
        )
        trigger = extract_triggering_user_context(fixture, turn)
        self.assertIsNotNone(trigger)
        assert trigger is not None
        self.assertIn("push the crate", trigger.get("content", ""))

    def test_wrong_commit_does_not_fallback_to_unrelated_event(self) -> None:
        from continuity_state_occurrence_evidence import (  # noqa: E402
            OccurrenceEvidence,
            TriggeringUser,
        )

        fixture = initialize_live_session(cast=["Alice"])
        fixture.manager.public_events.append(
            PublicEvent(
                event_id="evt-other",
                timestamp=datetime.now(timezone.utc),
                event_type="action",
                participants=["Alice"],
                summary="Other event",
                turn_index=1,
                known_by=["Alice"],
                occurrence_evidence=OccurrenceEvidence(
                    contributions=(),
                    triggering_user=TriggeringUser(
                        entry_id="u-x",
                        speaker="Player",
                        content="Unrelated action",
                    ),
                ),
            )
        )
        turn = CharacterTurnRecord(
            character_id="Alice",
            committed_move={"move_schema_version": 2, "beats": []},
            domain_commit_id="commit-missing",
            continuity_turn_index=2,
            director_decision={},
        )
        self.assertIsNone(extract_triggering_user_context(fixture, turn))


class CognitionFailureAuditTests(unittest.TestCase):
    def test_record_environment_cognition_failure_persists_audit(self) -> None:
        fixture = initialize_live_session(cast=["Alice"])
        turn = CharacterTurnRecord(
            character_id="Alice",
            committed_move={"move_schema_version": 2, "beats": []},
            domain_commit_id="commit-fail",
            continuity_turn_index=3,
            director_decision={},
        )
        audit = record_environment_cognition_failure(
            fixture,
            turn,
            failure_stage="substrate_exception",
            failure_reason="import_error",
        )
        self.assertTrue(audit["cognition_failed"])
        stored = fixture.manager.turn_metadata_by_index[3]["narrator_environment_audit"]
        self.assertEqual(stored["failure_reason"], "import_error")


class NarratorContextIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self.repo = SessionRepository(self._tmpdir)
        self.kernel = DomainKernel.for_repository(self.repo)

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
