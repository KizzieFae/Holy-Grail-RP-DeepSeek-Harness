"""Authoritative Holy Grail domain kernel for the V2 boundary prototype."""

from __future__ import annotations

import copy
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from character_move_adapters import legacy_move_text_for_validation  # noqa: E402
from director_decision_contract import (  # noqa: E402
    normalize_environment_event,
    normalize_tension_shift,
)
from narrator_presentation_validation import (  # noqa: E402
    validate_narrator_presentation as validate_narrator_presentation_rules,
)
from perception_audibility_structured import redact_structured_move_for_orchestration  # noqa: E402
from prompt_builders import build_narrator_render_prompt  # noqa: E402
from response_validation import validate_bot_response_for_runtime  # noqa: E402
from response_validation_selection import (  # noqa: E402
    eligible_agent_keys_for_present_characters,
    get_available_actors,
)
from response_validation_parsing import (  # noqa: E402
    parse_character_move,
    parse_director_decision,
)
from issue240_semantic_evaluation import (  # noqa: E402
    issue240_semantic_evaluation_enabled,
    normalize_issue240_semantic_evaluation_for_continuity,
)
from domain.modules.authority_reference import validate_authority_references  # noqa: E402

from .contract import (  # noqa: E402
    CommitRequest,
    CommitResponse,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorContextPrepareResponse,
    DirectorDecisionResult,
    DirectorDecisionValidationRequest,
    DirectorSemanticQaContextPrepareRequest,
    EligibleActorsRequest,
    EligibleActorsResponse,
    EligibleActorEntry,
    OpeningContextPrepareRequest,
    OpeningPersistRequest,
    NarratorContextPrepareRequest,
    NarratorPresentationValidationRequest,
    NarratorPresentationValidationResponse,
    NarratorSemanticQaContextPrepareRequest,
    ParticipationDecision,
    ParticipationDecisionRequest,
    PromptContribution,
    PromptContributionManifest,
    RoundStartRequest,
    RoundStartResponse,
    SceneStateSnapshot,
    SessionInfoResponse,
    SessionHistoryResponse,
    PresentationRecordRequest,
    UserTurnRecordRequest,
    PlayerSkipRecordRequest,
    UserProfileSetRequest,
    ValidationRequest,
    ValidationResponse,
    SemanticEvaluationContextPrepareRequest,
    SemanticEvaluationContextResponse,
    SemanticQaContextPrepareResponse,
)
from .character_context_projector import build_character_lane_contributions  # noqa: E402
from .character_conversation_projection import (  # noqa: E402
    project_character_conversation_for_manifest,
)
from .continuity_context_projector import (  # noqa: E402
    AuthoritativeContextContribution,
    collect_recent_environment_evidence,
    project_authoritative_context,
)
from .director_context_digests import (  # noqa: E402
    build_director_scene_evidence_contributions,
    director_scene_condition_flags,
    validate_director_context_completeness,
)
from .director_semantic_qa_context import (  # noqa: E402
    build_director_semantic_qa_context_response,
    prepare_director_semantic_qa_context,
)
from .narrator_semantic_qa_context import (  # noqa: E402
    build_narrator_semantic_qa_context_response,
    prepare_narrator_semantic_qa_context,
)
from .fixture_store import FixtureStore  # noqa: E402
from .participation_policy import evaluate_participation_policy  # noqa: E402
from .semantic_evaluation_context import (  # noqa: E402
    prepare_semantic_evaluation_context as build_semantic_evaluation_context,
)
from .session_history import (  # noqa: E402
    INFERENCE_OUTCOME_EMPTY_OUTPUT,
    INFERENCE_OUTCOME_INFERENCE_ERROR,
    INFERENCE_OUTCOME_SUCCEEDED,
    PLAYER_SKIP_CONTENT,
    PLAYER_SKIP_KIND,
    PRESENTATION_SOURCE_COMMITTED_FALLBACK,
    PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC,
    PRESENTATION_SOURCE_NARRATOR,
    append_history_entry,
    project_history_to_transcript,
    summarize_committed_move,
)
from .session_repository import (  # noqa: E402
    CommitDedupRecord,
    PersistenceError,
    SessionRepository,
)
from .opening_prompt import build_opening_generation_instruction  # noqa: E402
from .player_identity import is_player_controlled  # noqa: E402
from .session_setup import setup_provenance_for_ui  # noqa: E402
from .memory_retrieval import build_session_memory_projection  # noqa: E402
from .memory_service import MemoryService  # noqa: E402
from .knowledge_service import KnowledgeService  # noqa: E402
from .librarian_contract import knowledge_access_request_from_dict  # noqa: E402
from .librarian_service import LibrarianService  # noqa: E402
from .librarian_proposal_service import LibrarianProposalService  # noqa: E402
from .storyteller_contract import (  # noqa: E402
    StorytellerAdvisoryPackage,
    StorytellerOrientationAssessment,
    advisory_package_from_dict,
    advisory_package_to_dict,
    invalidate_storyteller_package,
)
from .storyteller_packaging_mapper import map_storyteller_package_to_contributions  # noqa: E402
from .storyteller_packaging_policy import StorytellerPackagingConsumer  # noqa: E402
from .librarian_packaging_validity import PackagingBindingContext  # noqa: E402
from .character_service import CharacterKnowledgeService  # noqa: E402
from .character_upstream_context import assemble_character_upstream_contributions  # noqa: E402
from .librarian_bundle_codec import librarian_knowledge_bundle_from_dict  # noqa: E402
from .librarian_packaging_mapper import map_librarian_bundle_to_contributions  # noqa: E402
from .storyteller_service import StorytellerService  # noqa: E402
from .memory_write_policy import (  # noqa: E402
    apply_character_turn_memory,
    apply_user_turn_memory,
    restore_character_states,
    snapshot_character_states,
)
from .setup_catalog import (  # noqa: E402
    list_characters_catalog,
    list_scene_templates_catalog,
    list_template_openers_catalog,
)
from .session_state import (  # noqa: E402
    CharacterTurnRecord,
    LiveSession,
    RoundFixture,
)

PROTOTYPE_VALID_MOVE: dict[str, Any] = {
    "move_schema_version": 2,
    "beats": [{"type": "action", "action": "nods thoughtfully"}],
    "motivation": {
        "goal": "acknowledge",
        "tactic": "subtle gesture",
        "emotional_driver": "calm",
        "risk_level": "low",
    },
    "semantic_evaluation": {"decision": "no_covered_change"},
}

PROTOTYPE_DIRECTOR_DECISION: dict[str, Any] = {
    "next_actor": "Alice",
    "end_round": False,
    "reason": "Alice has not spoken yet.",
    "environment_event": "",
    "tension_shift": "",
}

PROTOTYPE_DIRECTOR_DECISION_BOB: dict[str, Any] = {
    "next_actor": "Bob",
    "end_round": False,
    "reason": "Bob has not spoken yet.",
    "environment_event": "",
    "tension_shift": "",
}

PROTOTYPE_DIRECTOR_END_ROUND: dict[str, Any] = {
    "next_actor": "",
    "end_round": True,
    "reason": "Both characters have acted this round.",
    "environment_event": "",
    "tension_shift": "",
}

PROTOTYPE_BOB_MOVE: dict[str, Any] = {
    "move_schema_version": 2,
    "beats": [{"type": "action", "action": "examines the blueprint Alice left on the table"}],
    "motivation": {
        "goal": "inspect",
        "tactic": "careful study",
        "emotional_driver": "curious",
        "risk_level": "low",
    },
    "semantic_evaluation": {"decision": "no_covered_change"},
}

PROTOTYPE_ALICE_BLUEPRINT_MOVE: dict[str, Any] = {
    "move_schema_version": 2,
    "beats": [{"type": "action", "action": "places the blueprint on the table"}],
    "motivation": {
        "goal": "share",
        "tactic": "visible placement",
        "emotional_driver": "helpful",
        "risk_level": "low",
    },
    "semantic_evaluation": {"decision": "no_covered_change"},
}

PROTOTYPE_ALICE_OFFSTAGE_MOVE: dict[str, Any] = {
    "move_schema_version": 2,
    "beats": [{"type": "action", "action": "steps into the hallway"}],
    "motivation": {
        "goal": "withdraw",
        "tactic": "leave the focal scene",
        "emotional_driver": "tense",
        "risk_level": "low",
    },
    "semantic_evaluation": {
        "decision": "covered_change",
        "proposals": [{"kind": "off_focal", "character": "Alice"}],
    },
}


class DomainKernel:
    def __init__(
        self,
        repository: SessionRepository | None = None,
        *,
        store: FixtureStore | None = None,
    ) -> None:
        if store is not None and repository is not None:
            raise ValueError("cannot specify both store and repository")
        if store is not None:
            self.store = store
        else:
            self.store = repository or SessionRepository()

    def _memory_service(self) -> MemoryService | None:
        if isinstance(self.store, SessionRepository):
            return self.store.memory_service
        return None

    def _knowledge_service(self) -> KnowledgeService | None:
        if isinstance(self.store, SessionRepository):
            return self.store.knowledge_service
        return None

    def _librarian_service(self) -> LibrarianService:
        knowledge = self._knowledge_service()
        scope_repo = knowledge.scope_repo if knowledge is not None else None
        from .retrieval_service import RetrievalService

        return LibrarianService(retrieval_service=RetrievalService(scope_repo=scope_repo))

    def _librarian_proposal_service(self) -> LibrarianProposalService:
        return LibrarianProposalService()

    def _session_scope(self, hg_scene_id: str):
        repository = self.store
        if isinstance(repository, SessionRepository):
            return repository.session_scope(hg_scene_id)
        from contextlib import nullcontext

        return nullcontext()

    def _storyteller_service(self) -> StorytellerService:
        return StorytellerService(librarian_service=self._librarian_service())

    def _character_knowledge_service(self) -> CharacterKnowledgeService:
        return CharacterKnowledgeService()

    def create_session(self, **kwargs: Any) -> SessionInfoResponse:
        session = self.store.create_session(**kwargs)
        return self._session_info(session)

    def open_session(self, hg_session_id: str) -> SessionInfoResponse:
        session = self.store.open_session(hg_session_id)
        return self._session_info(session)

    def record_user_turn(self, req: UserTurnRecordRequest) -> dict[str, Any]:
        fixture = self.store.require(req.hg_session_id)
        memory_service = self._memory_service()
        char_snapshot = (
            memory_service.snapshot_character_states(fixture)
            if memory_service is not None
            else snapshot_character_states(fixture)
        )
        history_before = (
            memory_service.relationship_history_snapshot(fixture, req.speaker)
            if memory_service is not None
            else {}
        )
        if memory_service is not None:
            memory_service.write_user_turn_memory(
                fixture, user_name=req.speaker, content=req.content
            )
        else:
            apply_user_turn_memory(
                fixture, user_name=req.speaker, content=req.content
            )
        entry = append_history_entry(
            fixture.rp_history,
            kind="user",
            content=req.content,
            actor_id=req.speaker,
            hg_round_id=req.hg_round_id,
            metadata={
                "forced_designation": req.forced_designation,
                "speaker": req.speaker,
            },
        )
        projection_records = []
        if memory_service is not None:
            projection_records = memory_service.build_user_relationship_projection(
                fixture,
                user_name=req.speaker,
                history_before=history_before,
                source_hg_round_id=req.hg_round_id,
            )
        if isinstance(self.store, SessionRepository):
            try:
                self.store.persist(fixture)
            except PersistenceError:
                if memory_service is not None:
                    memory_service.restore_character_states(fixture, char_snapshot)
                else:
                    restore_character_states(fixture, char_snapshot)
                fixture.rp_history.pop()
                raise
            if memory_service is not None:
                memory_service.project_cross_scope_after_persist(fixture, projection_records)
        return entry

    def record_player_skip(self, req: PlayerSkipRecordRequest) -> dict[str, Any]:
        fixture = self.store.require(req.hg_session_id)
        entry = append_history_entry(
            fixture.rp_history,
            kind=PLAYER_SKIP_KIND,
            content=PLAYER_SKIP_CONTENT,
            actor_id=req.speaker,
            metadata={
                "intent": "player_skip",
                "speaker": req.speaker,
            },
        )
        if isinstance(self.store, SessionRepository):
            self.store.persist(fixture)
        return entry

    def record_presentation(self, req: PresentationRecordRequest) -> dict[str, Any]:
        from narrator_presentation_fallback import render_degraded_player_presentation

        fixture = self.store.require(req.hg_session_id)
        status = "failed" if req.presentation_failed else "rendered"
        content = (req.presentation_text or "").strip()
        committed = None
        structured_move: dict[str, Any] | None = None
        if req.domain_commit_id:
            committed = next(
                (
                    item
                    for item in reversed(fixture.rp_history)
                    if item.get("kind") == "committed_turn"
                    and item.get("domain_commit_id") == req.domain_commit_id
                ),
                None,
            )
            if committed is not None:
                move = (committed.get("metadata") or {}).get("structured_move")
                if isinstance(move, dict):
                    structured_move = move
            if structured_move is None:
                for rnd in fixture.rounds:
                    turn_record = next(
                        (
                            turn
                            for turn in rnd.character_turns
                            if turn.domain_commit_id == req.domain_commit_id
                        ),
                        None,
                    )
                    if turn_record is not None:
                        structured_move = dict(turn_record.committed_move)
                        break
        character_name = str(
            req.character_id
            or (committed or {}).get("actor_id")
            or "Character"
        )
        if not content:
            if isinstance(structured_move, dict):
                content = render_degraded_player_presentation(
                    structured_move,
                    character_name=character_name,
                )
            elif committed is not None:
                content = str(committed.get("content") or "[presentation unavailable]")
            else:
                content = "[presentation unavailable]"
        presentation_source = PRESENTATION_SOURCE_NARRATOR
        presentation_degraded = False
        if req.presentation_failed:
            if isinstance(structured_move, dict):
                presentation_source = PRESENTATION_SOURCE_DEGRADED_DETERMINISTIC
                presentation_degraded = True
            else:
                presentation_source = PRESENTATION_SOURCE_COMMITTED_FALLBACK
            inference_outcome = req.inference_outcome or (
                INFERENCE_OUTCOME_EMPTY_OUTPUT
                if not (req.presentation_text or "").strip()
                else INFERENCE_OUTCOME_INFERENCE_ERROR
            )
        else:
            inference_outcome = req.inference_outcome or INFERENCE_OUTCOME_SUCCEEDED
        entry = append_history_entry(
            fixture.rp_history,
            kind="presentation",
            content=content,
            hg_round_id=req.hg_round_id,
            domain_commit_id=req.domain_commit_id,
            actor_id=req.character_id,
            presentation_status=status,
            metadata={
                "renderer": "narrator",
                "presentation_source": presentation_source,
                "presentation_degraded": presentation_degraded,
                "inference_outcome": inference_outcome,
            },
        )
        if isinstance(self.store, SessionRepository):
            self.store.persist(fixture)
        return entry

    def get_session_history(self, hg_session_id: str) -> SessionHistoryResponse:
        fixture = self.store.require(hg_session_id)
        entries = tuple(dict(item) for item in fixture.rp_history)
        transcript = tuple(project_history_to_transcript(fixture.rp_history))
        return SessionHistoryResponse(
            hg_session_id=hg_session_id,
            entries=entries,
            transcript=transcript,
        )

    def create_scene(self, **kwargs: Any) -> LiveSession:
        """Transitional prototype scene creation; prefer create_session in production."""
        return self.store.create_scene(**kwargs)

    def _session_info(self, session: LiveSession) -> SessionInfoResponse:
        mgr = session.manager
        assert mgr.scene_state is not None
        present = tuple(
            str(name)
            for name in (getattr(mgr.scene_state, "present_characters", None) or session.cast)
        )
        return SessionInfoResponse(
            hg_session_id=session.hg_session_id,
            hg_scene_id=session.hg_scene_id,
            turn_counter=int(mgr.turn_counter),
            continuity_version=int(session.continuity_version),
            committed_move_count=int(session.committed_move_count),
            present_characters=present,
            location=str(mgr.scene_state.location or ""),
            setup_provenance=setup_provenance_for_ui(session.setup_snapshot) or None,
            character_file_ids=dict(session.character_file_ids) or None,
            memory_scope_id=session.memory_scope_id or None,
        )

    def list_memory_scopes(self) -> list[dict[str, str]]:
        memory_service = self._memory_service()
        if memory_service is None:
            return []
        return memory_service.list_memory_scopes()

    def list_characters(self) -> list[dict[str, Any]]:
        return list_characters_catalog()

    def list_scene_templates(self) -> list[dict[str, Any]]:
        return list_scene_templates_catalog()

    def list_template_openers(self, template_id: str) -> list[dict[str, Any]]:
        return list_template_openers_catalog(template_id)

    def scene_snapshot(self, hg_scene_id: str) -> SceneStateSnapshot:
        fixture = self.store.require(hg_scene_id)
        info = self._session_info(fixture)
        return SceneStateSnapshot(
            hg_scene_id=hg_scene_id,
            location=info.location,
            turn_counter=info.turn_counter,
            present_characters=info.present_characters,
            committed_move_count=info.committed_move_count,
            hg_session_id=info.hg_session_id,
            continuity_version=info.continuity_version,
        )

    def start_round(self, req: RoundStartRequest) -> RoundStartResponse:
        fixture = self.store.require(req.hg_scene_id)
        mgr = fixture.manager
        round_id = f"hg-round-{uuid.uuid4()}"
        fixture.rounds.append(
            RoundFixture(
                hg_round_id=round_id,
                hg_scene_id=req.hg_scene_id,
                turn_index=int(mgr.turn_counter),
            )
        )
        return RoundStartResponse(
            hg_scene_id=req.hg_scene_id,
            hg_round_id=round_id,
            turn_index=int(mgr.turn_counter),
        )

    def _require_round(self, fixture: LiveSession, hg_round_id: str) -> RoundFixture:
        for rnd in fixture.rounds:
            if rnd.hg_round_id == hg_round_id:
                return rnd
        raise KeyError(f"unknown hg_round_id: {hg_round_id}")

    def _eligibility_snapshot_id(self, rnd: RoundFixture) -> str:
        return f"{rnd.hg_round_id}:{rnd.eligibility_epoch}"

    def _active_storyteller_package(
        self, rnd: RoundFixture
    ) -> StorytellerAdvisoryPackage | None:
        stored = rnd.storyteller_advisory_package
        if not stored:
            return None
        package = advisory_package_from_dict(stored)
        if not package.validity.is_valid:
            return None
        return package

    def _storyteller_packaging_binding(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        package: StorytellerAdvisoryPackage,
        *,
        pipeline_stage: str,
    ) -> PackagingBindingContext:
        return PackagingBindingContext(
            hg_round_id=rnd.hg_round_id,
            turn_index=int(rnd.turn_index),
            pipeline_stage=pipeline_stage,
            continuity_version=int(fixture.continuity_version),
            authoritative_snapshot_id=package.validity.valid_from_authoritative_snapshot_id,
        )

    def _storyteller_contributions_for_role(
        self,
        fixture: LiveSession,
        rnd: RoundFixture,
        *,
        manifest_id: str,
        consumer_target: StorytellerPackagingConsumer,
        character_id: str | None = None,
    ) -> tuple[PromptContribution, ...]:
        package = self._active_storyteller_package(rnd)
        if package is None:
            return ()
        result = map_storyteller_package_to_contributions(
            package,
            manifest_id=manifest_id,
            consumer_target=consumer_target,
            binding=self._storyteller_packaging_binding(
                fixture,
                rnd,
                package,
                pipeline_stage=consumer_target,
            ),
            character_id=character_id,
        )
        return result.contributions

    def _invalidate_storyteller_package_for_round(
        self,
        rnd: RoundFixture,
        *,
        reason: str,
    ) -> str | None:
        stored = rnd.storyteller_advisory_package
        if not stored:
            return None
        package = advisory_package_from_dict(stored)
        if not package.validity.is_valid:
            return rnd.storyteller_invalidation_reason
        invalidated = invalidate_storyteller_package(package, reason=reason)
        rnd.storyteller_advisory_package = advisory_package_to_dict(invalidated)
        rnd.storyteller_invalidation_reason = reason
        return reason

    def bind_storyteller_advisory_package(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        package: dict[str, Any],
        audit: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        if not package:
            return {"accepted": False, "reason": "missing_package", "package_id": None}
        parsed = advisory_package_from_dict(package)
        if parsed.hg_round_id and parsed.hg_round_id != rnd.hg_round_id:
            return {
                "accepted": False,
                "reason": "round_mismatch",
                "package_id": parsed.package_id,
            }
        if not parsed.validity.is_valid:
            return {
                "accepted": False,
                "reason": parsed.validity.invalidation_reason or "package_invalid",
                "package_id": parsed.package_id,
            }
        rnd.storyteller_advisory_package = advisory_package_to_dict(parsed)
        rnd.storyteller_round_audit = dict(audit) if audit else None
        rnd.storyteller_invalidation_reason = None
        director_preview = map_storyteller_package_to_contributions(
            parsed,
            manifest_id=f"manifest-director-preview-{parsed.package_id}",
            consumer_target="director",
            binding=self._storyteller_packaging_binding(
                fixture,
                rnd,
                parsed,
                pipeline_stage="director",
            ),
        )
        return {
            "accepted": True,
            "reason": "ok",
            "package_id": parsed.package_id,
            "degradation_level": parsed.degradation.level,
            "validity": {
                "is_valid": parsed.validity.is_valid,
                "bound_hg_round_id": parsed.validity.bound_hg_round_id,
            },
            "mapped_preview": {
                "director": {
                    "items_mapped": director_preview.items_mapped,
                    "source_kinds": sorted(
                        {item.source_kind for item in director_preview.contributions}
                    ),
                }
            },
            "audit": rnd.storyteller_round_audit,
        }

    def get_storyteller_round_state(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        stored = rnd.storyteller_advisory_package
        package = advisory_package_from_dict(stored) if stored else None
        return {
            "hg_scene_id": hg_scene_id,
            "hg_round_id": hg_round_id,
            "package_id": package.package_id if package else None,
            "is_valid": bool(package and package.validity.is_valid),
            "invalidation_reason": rnd.storyteller_invalidation_reason,
            "degradation_level": package.degradation.level if package else None,
            "audit": rnd.storyteller_round_audit,
        }

    def _normalize_director_auxiliary_fields(
        self,
        fixture: LiveSession,
        decision: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(decision)
        normalized["tension_shift"] = normalize_tension_shift(
            decision.get("tension_shift")
        )
        normalized["environment_event"] = normalize_environment_event(
            decision.get("environment_event"),
            recent_committed_events=collect_recent_environment_evidence(fixture),
        )
        return normalized

    def _presence_status(self, fixture: LiveSession, character_id: str) -> str:
        mgr = fixture.manager
        assert mgr.scene_state is not None
        offstage = set(getattr(mgr.scene_state, "offstage_characters", None) or [])
        present = set(getattr(mgr.scene_state, "present_characters", None) or [])
        absent = set(getattr(mgr.scene_state, "absent_but_relevant", None) or [])
        if character_id in offstage:
            return "offstage"
        if character_id in present:
            return "present"
        if character_id in absent:
            return "absent_but_relevant"
        if character_id in fixture.cast:
            return "not_present"
        return "not_in_cast"

    def _exclusion_reason(
        self, fixture: LiveSession, rnd: RoundFixture, character_id: str
    ) -> str | None:
        if character_id not in fixture.cast:
            return "not_in_cast"
        if character_id in rnd.actors_used_this_round:
            return "already_used_this_round"
        presence = self._presence_status(fixture, character_id)
        if presence == "offstage":
            return "offstage"
        if presence == "absent_but_relevant":
            return "absent_but_relevant"
        if presence == "not_present":
            return "not_present"
        if is_player_controlled(fixture.setup_snapshot, character_id):
            return "player_controlled"
        return None

    def _eligibility_projection(
        self, fixture: LiveSession, rnd: RoundFixture
    ) -> tuple[list[str], tuple[EligibleActorEntry, ...]]:
        mgr = fixture.manager
        assert mgr.scene_state is not None
        present_labels = list(getattr(mgr.scene_state, "present_characters", None) or fixture.cast)
        eligible_present = eligible_agent_keys_for_present_characters(
            present_labels,
            list(fixture.cast),
            display_name_for_key=lambda key: key,
        )
        offstage = list(getattr(mgr.scene_state, "offstage_characters", None) or [])
        available = get_available_actors(
            list(fixture.cast),
            list(rnd.actors_used_this_round),
            eligible_present,
            offstage,
        )
        available = [
            actor
            for actor in available
            if not is_player_controlled(fixture.setup_snapshot, actor)
        ]
        actors: list[EligibleActorEntry] = []
        for character_id in fixture.cast:
            exclusion = self._exclusion_reason(fixture, rnd, character_id)
            actors.append(
                EligibleActorEntry(
                    character_id=character_id,
                    eligibility_status="eligible" if character_id in available else "ineligible",
                    presence_status=self._presence_status(fixture, character_id),
                    exclusion_reason=exclusion,
                )
            )
        return available, tuple(actors)

    def _available_actors(self, fixture: LiveSession, rnd: RoundFixture) -> list[str]:
        available, _ = self._eligibility_projection(fixture, rnd)
        return available

    def eligible_actors(self, req: EligibleActorsRequest) -> EligibleActorsResponse:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        available, actors = self._eligibility_projection(fixture, rnd)
        role_assignments = dict(getattr(mgr.scene_state, "role_assignments", {}) or {})
        character_roles = {
            name: str(role_assignments.get(name, "guest")) for name in fixture.cast
        }
        return EligibleActorsResponse(
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            eligibility_snapshot_id=self._eligibility_snapshot_id(rnd),
            eligible_actors=tuple(available),
            actors_used_this_round=tuple(rnd.actors_used_this_round),
            character_roles=character_roles,
            actors=actors,
            present_characters=tuple(
                str(name)
                for name in (getattr(mgr.scene_state, "present_characters", None) or ())
            ),
            offstage_characters=tuple(
                str(name)
                for name in (getattr(mgr.scene_state, "offstage_characters", None) or ())
            ),
            absent_but_relevant=tuple(
                str(name)
                for name in (getattr(mgr.scene_state, "absent_but_relevant", None) or ())
            ),
        )

    def participation_decision(
        self, req: ParticipationDecisionRequest
    ) -> ParticipationDecision:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        eligibility = self.eligible_actors(
            EligibleActorsRequest(hg_scene_id=req.hg_scene_id, hg_round_id=req.hg_round_id)
        )
        return evaluate_participation_policy(
            fixture=fixture,
            rnd=rnd,
            eligibility=eligibility,
            eligibility_snapshot_id=req.eligibility_snapshot_id,
            forced_designation=req.forced_designation,
        )

    @staticmethod
    def _auth_contributions_to_prompt(
        manifest_id: str,
        projections: list[AuthoritativeContextContribution],
    ) -> list[PromptContribution]:
        return [
            PromptContribution(
                contribution_id=f"{manifest_id}-{proj.source_kind}",
                source_kind=proj.source_kind,  # type: ignore[arg-type]
                authority_class=proj.authority_class,  # type: ignore[arg-type]
                knowledge_ids=proj.knowledge_ids,
                priority=proj.priority,
                content=proj.content,
                provenance=dict(proj.provenance),
            )
            for proj in projections
        ]

    def prepare_director_context(
        self, req: DirectorContextPrepareRequest
    ) -> DirectorContextPrepareResponse:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        manifest_id = f"manifest-director-{req.inference_id}-{req.attempt_index}"
        used = list(req.actors_used_this_round) or list(rnd.actors_used_this_round)
        available = self._available_actors(fixture, rnd)
        auth_projections = project_authoritative_context(
            fixture,
            role="director",
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            turn_index=req.turn_index,
            actors_used_this_round=used,
            eligible_actors=available,
        )
        scene_contributions, authority_refs = build_director_scene_evidence_contributions(
            fixture,
            rnd,
            manifest_id,
            available,
            auth_contributions=list(
                self._auth_contributions_to_prompt(manifest_id, auth_projections)
            ),
        )
        contributions: list[PromptContribution] = list(scene_contributions)
        contributions.extend(
            self._storyteller_contributions_for_role(
                fixture,
                rnd,
                manifest_id=manifest_id,
                consumer_target="director",
            )
        )
        contributions.extend(
            (
                PromptContribution(
                    contribution_id=f"{manifest_id}-director-scratch",
                    source_kind="director_scratch",
                    authority_class="derived",
                    knowledge_ids=(f"director:{req.inference_id}",),
                    priority=20,
                    content=(
                        "Director scratch: weigh participation balance and select the next actor. "
                        "Do not assume character-private knowledge."
                    ),
                    provenance={"inference_id": req.inference_id, "role": "director"},
                ),
                PromptContribution(
                    contribution_id=f"{manifest_id}-instruction",
                    source_kind="inference_instruction",
                    authority_class="derived",
                    knowledge_ids=(f"inference:{req.inference_id}",),
                    priority=30,
                    content=(
                        "Output only JSON with next_actor, end_round, reason, environment_event, "
                        "tension_shift. tension_shift must be escalate, soften, or steady. "
                        "environment_event is optional; use an empty string rather than repeating "
                        "a recent accepted environment development."
                    ),
                    provenance={"inference_id": req.inference_id},
                ),
            )
        )
        correction = req.correction_context
        if isinstance(correction, dict) and correction:
            contributions.insert(
                -1,
                PromptContribution(
                    contribution_id=f"{manifest_id}-semantic-correction",
                    source_kind="semantic_correction",
                    authority_class="suggestive",
                    knowledge_ids=(
                        str(correction.get("evaluation_pass_id") or req.inference_id),
                    ),
                    priority=29,
                    content=json.dumps(correction, ensure_ascii=False, indent=2),
                    provenance={
                        "inference_id": req.inference_id,
                        "visibility": "orchestration_only",
                        "attempt_index": req.attempt_index,
                    },
                ),
            )
        flags = director_scene_condition_flags(fixture, rnd, available)
        context_completeness = validate_director_context_completeness(
            contributions,
            has_round_turns=flags["has_round_turns"],
            multiple_eligible=flags["multiple_eligible"],
            has_active_issues=flags["has_active_issues"],
            has_user_turn=flags["has_user_turn"],
        )
        normalized_refs, ref_errors = validate_authority_references(authority_refs)
        if ref_errors:
            raise ValueError(
                "Director context preparation failed: " + "; ".join(ref_errors)
            )
        return DirectorContextPrepareResponse(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            role="director",
            character_id=None,
            turn_index=rnd.turn_index,
            attempt_index=req.attempt_index,
            contributions=tuple(contributions),
            authority_references=tuple(normalized_refs),
            context_completeness=context_completeness,
        )

    def prepare_director_semantic_qa_context(
        self, req: DirectorSemanticQaContextPrepareRequest
    ) -> SemanticQaContextPrepareResponse:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        used = list(req.actors_used_this_round) or list(rnd.actors_used_this_round)
        available = self._available_actors(fixture, rnd)
        auth_projections = project_authoritative_context(
            fixture,
            role="director",
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            turn_index=req.turn_index,
            actors_used_this_round=used,
            eligible_actors=available,
        )
        manifest_id = f"manifest-director-semantic-qa-{req.evaluation_pass_id}"
        role_contributions, authority_refs, candidate_package = (
            prepare_director_semantic_qa_context(
                fixture,
                rnd,
                req,
                available=available,
                auth_contributions_fn=self._auth_contributions_to_prompt,
                auth_projections=auth_projections,
            )
        )
        return build_director_semantic_qa_context_response(
            manifest_id=manifest_id,
            evaluation_pass_id=req.evaluation_pass_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            turn_index=rnd.turn_index,
            role_contributions=role_contributions,
            authority_references=authority_refs,
            candidate_package=candidate_package,
        )

    def prepare_context(self, req: ContextPrepareRequest) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        manifest_id = f"manifest-character-{req.inference_id}-{req.attempt_index}"
        private_secret = fixture.character_private_secrets.get(req.character_id, "")
        memory_service = self._memory_service()
        if memory_service is not None:
            memory_projections = memory_service.retrieve_memory_contributions(
                fixture, character_id=req.character_id
            )
        else:
            single = build_session_memory_projection(
                fixture.character_states.get(req.character_id)
            )
            memory_projections = [single] if single is not None else []
        upstream = assemble_character_upstream_contributions(
            fixture,
            rnd,
            manifest_id=manifest_id,
            character_id=req.character_id,
            role=req.role,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            turn_index=req.turn_index,
            director_decision=req.director_decision,
            correction_context=req.correction_context,
            memory_projections=memory_projections,
            private_secret=private_secret,
            auth_contributions_fn=self._auth_contributions_to_prompt,
            storyteller_contributions_fn=self._storyteller_contributions_for_role,
            include_correction=True,
        )
        contributions: list[PromptContribution] = list(upstream.contributions)
        librarian_audit = dict(req.librarian_knowledge_audit or {})
        if isinstance(req.librarian_bundle, dict) and req.librarian_bundle:
            try:
                bundle = librarian_knowledge_bundle_from_dict(req.librarian_bundle)
                binding = PackagingBindingContext(
                    hg_round_id=req.hg_round_id,
                    turn_index=req.turn_index,
                    pipeline_stage="character",
                    continuity_version=int(fixture.continuity_version),
                    authoritative_snapshot_id=(
                        f"cv:{fixture.continuity_version}:scene:{req.hg_scene_id}:round:{req.hg_round_id}"
                    ),
                    bound_character_id=req.character_id,
                )
                packaging = map_librarian_bundle_to_contributions(
                    bundle,
                    manifest_id=manifest_id,
                    consumer_target="character",
                    binding=binding,
                )
                librarian_audit.update(
                    {
                        "bundle_id": bundle.bundle_id,
                        "eligibility_accepted": packaging.eligibility.accepted,
                        "eligibility_reason": packaging.eligibility.reason,
                        "rejection_codes": list(packaging.eligibility.rejection_codes),
                        "entries_considered": packaging.entries_considered,
                        "entries_mapped": packaging.entries_mapped,
                        "mediation_mode": bundle.mediation_mode,
                        "omitted_reason": packaging.omitted_reason,
                    }
                )
                if packaging.contributions:
                    contributions.extend(packaging.contributions)
            except (KeyError, TypeError, ValueError) as exc:
                librarian_audit.update(
                    {
                        "bundle_decode_error": str(exc),
                        "eligibility_accepted": False,
                    }
                )
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-instruction",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"inference:{req.inference_id}",),
                priority=30,
                content=(
                    "Output only valid JSON for move_schema_version 2 with non-empty beats[], "
                    "motivation object, and semantic_evaluation. "
                    "Each beat must be type action (key action) or type speech (key dialogue). "
                    "Action-only, speech-only, and mixed beat sequences are all valid when "
                    "appropriate to the scene."
                ),
                provenance={
                    "inference_id": req.inference_id,
                    **({"librarian_knowledge_audit": librarian_audit} if librarian_audit else {}),
                },
            ),
        )
        return PromptContributionManifest(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            role="character",
            character_id=req.character_id,
            turn_index=req.turn_index,
            attempt_index=req.attempt_index,
            contributions=contributions,
        )

    def prepare_semantic_evaluation_context(
        self, req: SemanticEvaluationContextPrepareRequest
    ) -> SemanticEvaluationContextResponse:
        fixture = self.store.require(req.hg_scene_id)
        manifest_id = f"manifest-semantic-eval-{req.evaluation_pass_id}"
        contributions, authority_refs, candidate_package = build_semantic_evaluation_context(
            fixture,
            req,
            auth_contributions_to_prompt=self._auth_contributions_to_prompt,
        )
        return SemanticEvaluationContextResponse(
            manifest_id=manifest_id,
            evaluation_pass_id=req.evaluation_pass_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            character_id=req.character_id,
            turn_index=req.turn_index,
            contributions=tuple(contributions),
            authority_references=tuple(authority_refs),
            candidate_package=candidate_package,
        )

    def prepare_librarian_mediation_context(
        self,
        *,
        hg_scene_id: str,
        inference_id: str,
        knowledge_access_request: dict[str, Any],
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        request = knowledge_access_request_from_dict(
            {**knowledge_access_request, "hg_scene_id": hg_scene_id}
        )
        response = self._librarian_service().prepare_mediation_context(
            request,
            fixture,
            inference_id=inference_id,
        )
        return {
            "manifest_id": response.manifest_id,
            "inference_id": response.inference_id,
            "request_id": response.request_id,
            "hg_scene_id": response.hg_scene_id,
            "hg_round_id": response.hg_round_id,
            "contributions": [
                {
                    "contribution_id": item.contribution_id,
                    "source_kind": item.source_kind,
                    "authority_class": item.authority_class,
                    "knowledge_ids": list(item.knowledge_ids),
                    "priority": item.priority,
                    "content": item.content,
                    "provenance": dict(item.provenance),
                }
                for item in response.contributions
            ],
            "mediation_catalog": [
                {
                    "source_id": item.source_id,
                    "source_kind": item.source_kind,
                    "stable_ref": item.stable_ref,
                    "information_class": item.information_class,
                    "authority_class": item.authority_class,
                    "visibility_scope": item.visibility_scope,
                    "source_tier": item.source_tier,
                    "temporal_relationship": item.temporal_relationship,
                    "content": item.content,
                    "provenance": dict(item.provenance),
                }
                for item in response.mediation_catalog
            ],
            "retrieval_request_ids": list(response.retrieval_request_ids),
            "candidate_ids_supplied": list(response.candidate_ids_supplied),
            "authoritative_snapshot_id": response.authoritative_snapshot_id,
            "retrieval_disposition": [
                {
                    "request_id": item.request_id,
                    "candidate_ids_returned": list(item.candidate_ids_returned),
                    "diagnostics": dict(item.diagnostics),
                    "retrieval_omitted": bool(item.retrieval_omitted),
                }
                for item in response.retrieval_disposition
            ],
        }

    def finalize_librarian_mediation(
        self,
        *,
        hg_scene_id: str,
        inference_id: str,
        knowledge_access_request: dict[str, Any],
        mediation_result: dict[str, Any] | None = None,
        allow_deterministic_fallback: bool | None = None,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        request = knowledge_access_request_from_dict(
            {**knowledge_access_request, "hg_scene_id": hg_scene_id}
        )
        bundle = self._librarian_service().access_knowledge(
            request,
            fixture,
            mediation_result=mediation_result,
            inference_id=inference_id,
            allow_deterministic_fallback=allow_deterministic_fallback,
        )
        from dataclasses import asdict

        return asdict(bundle)

    def prepare_character_orientation_context(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        inference_id: str,
        character_id: str,
        role: str,
        turn_index: int,
        director_decision: dict[str, Any] | None = None,
        correction_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        private_secret = fixture.character_private_secrets.get(character_id, "")
        memory_service = self._memory_service()
        if memory_service is not None:
            memory_projections = memory_service.retrieve_memory_contributions(
                fixture, character_id=character_id
            )
        else:
            single = build_session_memory_projection(
                fixture.character_states.get(character_id)
            )
            memory_projections = [single] if single is not None else []
        return self._character_knowledge_service().prepare_orientation_context(
            fixture,
            rnd,
            inference_id=inference_id,
            character_id=character_id,
            role=role,
            turn_index=turn_index,
            director_decision=director_decision,
            correction_context=correction_context,
            memory_projections=memory_projections,
            private_secret=private_secret,
            auth_contributions_fn=self._auth_contributions_to_prompt,
            storyteller_contributions_fn=self._storyteller_contributions_for_role,
        )

    def finalize_character_orientation(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        inference_id: str,
        character_id: str,
        turn_index: int,
        orientation_result: dict[str, Any],
        upstream_fingerprint: str,
        director_decision: dict[str, Any] | None = None,
        correction_context: dict[str, Any] | None = None,
        storyteller_package_id: str | None = None,
        storyteller_valid: bool | None = None,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        return self._character_knowledge_service().finalize_orientation(
            fixture,
            rnd,
            inference_id=inference_id,
            character_id=character_id,
            turn_index=turn_index,
            orientation_result=orientation_result,
            upstream_fingerprint=upstream_fingerprint,
            director_decision=director_decision,
            correction_context=correction_context,
            storyteller_package_id=storyteller_package_id,
            storyteller_valid=storyteller_valid,
        )

    def prepare_librarian_proposal_context(
        self,
        *,
        hg_scene_id: str,
        inference_id: str,
        proposal_context_request: dict[str, Any],
    ) -> dict[str, Any]:
        from .librarian_proposal_contract import proposal_context_request_from_dict
        from .librarian_proposal_service import find_terminal_audit_for_commit

        with self._session_scope(hg_scene_id):
            fixture = self.store.require(hg_scene_id)
            request = proposal_context_request_from_dict(
                {**proposal_context_request, "hg_scene_id": hg_scene_id, "librarian_inference_id": inference_id}
            )
            existing = find_terminal_audit_for_commit(fixture, request.domain_commit_id)
            if existing is not None:
                return {
                    "skipped": True,
                    "orchestration_status": "already_terminal",
                    "domain_commit_id": request.domain_commit_id,
                    "existing_audit": existing,
                    "manifest_id": None,
                    "inference_id": inference_id,
                    "request_id": request.request_id,
                    "hg_scene_id": hg_scene_id,
                    "hg_round_id": request.hg_round_id,
                    "authoritative_snapshot_id": None,
                    "contributions": [],
                    "evidence_catalog": [],
                }
            response = self._librarian_proposal_service().prepare_proposal_context(request, fixture)
            return {
                "skipped": False,
                "orchestration_status": "prepared",
                "manifest_id": response.manifest_id,
                "inference_id": response.inference_id,
                "request_id": response.request_id,
                "hg_scene_id": response.hg_scene_id,
                "hg_round_id": response.hg_round_id,
                "domain_commit_id": response.domain_commit_id,
                "authoritative_snapshot_id": response.authoritative_snapshot_id,
                "contributions": [
                    {
                        "contribution_id": item.contribution_id,
                        "source_kind": item.source_kind,
                        "authority_class": item.authority_class,
                        "knowledge_ids": list(item.knowledge_ids),
                        "priority": item.priority,
                        "content": item.content,
                        "provenance": dict(item.provenance),
                    }
                    for item in response.contributions
                ],
                "evidence_catalog": [
                    {
                        "anchor_id": item.anchor_id,
                        "evidence_kind": item.evidence_kind,
                        "stable_ref": item.stable_ref,
                        "authority_class": item.authority_class,
                        "visibility_scope": item.visibility_scope,
                        "anchor_commit_id": item.anchor_commit_id,
                        "anchor_path": item.anchor_path,
                        "content": item.content,
                        "provenance": dict(item.provenance),
                    }
                    for item in response.evidence_catalog
                ],
            }

    def finalize_librarian_proposals(
        self,
        *,
        hg_scene_id: str,
        inference_id: str,
        proposal_context_request: dict[str, Any],
        proposal_result: dict[str, Any] | None = None,
        evidence_catalog: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        from dataclasses import asdict

        from .librarian_proposal_contract import (
            ProposalEvidenceCatalogItem,
            proposal_context_request_from_dict,
        )
        from .librarian_proposal_service import find_terminal_audit_for_commit

        with self._session_scope(hg_scene_id):
            fixture = self.store.require(hg_scene_id)
            request = proposal_context_request_from_dict(
                {**proposal_context_request, "hg_scene_id": hg_scene_id, "librarian_inference_id": inference_id}
            )
            existing = find_terminal_audit_for_commit(fixture, request.domain_commit_id)
            if existing is not None:
                return {
                    "skipped": True,
                    "orchestration_status": "already_terminal",
                    "domain_commit_id": request.domain_commit_id,
                    "batch_id": existing.get("librarian_proposal_batch_id"),
                    "request_id": existing.get("request_id"),
                    "degradation_mode": existing.get("degradation_mode", "none"),
                    "audit": existing,
                }
            manager_snapshot = None
            if isinstance(self.store, SessionRepository):
                manager_snapshot = self.store.snapshot_manager(fixture)
            catalog: tuple[ProposalEvidenceCatalogItem, ...] | None = None
            if evidence_catalog:
                catalog = tuple(
                    ProposalEvidenceCatalogItem(
                        anchor_id=str(item["anchor_id"]),
                        evidence_kind=str(item["evidence_kind"]),
                        stable_ref=str(item["stable_ref"]),
                        authority_class=item["authority_class"],  # type: ignore[arg-type]
                        visibility_scope=str(item.get("visibility_scope") or "public"),
                        content=str(item.get("content") or ""),
                        anchor_commit_id=item.get("anchor_commit_id"),
                        anchor_path=item.get("anchor_path"),
                        provenance=dict(item.get("provenance") or {}),
                    )
                    for item in evidence_catalog
                )
            result = self._librarian_proposal_service().finalize_proposals(
                request,
                fixture,
                proposal_result=proposal_result,
                evidence_catalog=catalog,
            )
            payload = asdict(result)
            if isinstance(self.store, SessionRepository):
                try:
                    if os.environ.get("HG_TEST_LIBRARIAN_PERSIST_FAIL") == "1":
                        raise PersistenceError("HG_TEST_LIBRARIAN_PERSIST_FAIL")
                    self.store.persist(fixture)
                except Exception:
                    audit_log = getattr(fixture, "librarian_proposal_audit_log", None)
                    if audit_log:
                        audit_log.pop()
                    if manager_snapshot is not None:
                        self.store.restore_manager(fixture, manager_snapshot)
                    raise
            payload["skipped"] = False
            payload["orchestration_status"] = "finalized"
            payload["persisted"] = isinstance(self.store, SessionRepository)
            return payload

    def prepare_storyteller_orientation_context(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        inference_id: str,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        return self._storyteller_service().prepare_orientation_context(
            fixture,
            rnd,
            inference_id=inference_id,
        )

    def finalize_storyteller_orientation(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        inference_id: str,
        orientation_result: dict[str, Any],
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        return self._storyteller_service().finalize_orientation(
            fixture,
            rnd,
            inference_id=inference_id,
            orientation_result=orientation_result,
        )

    def prepare_storyteller_assessment_context(
        self,
        *,
        hg_scene_id: str,
        inference_id: str,
        orientation: dict[str, Any],
        bundle: dict[str, Any],
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        orientation_obj = StorytellerOrientationAssessment(
            orientation_id=str(orientation["orientation_id"]),
            hg_round_id=str(orientation["hg_round_id"]),
            turn_index=int(orientation.get("turn_index", 0)),
            trigger=orientation.get("trigger", "round_start"),  # type: ignore[arg-type]
            information_gaps=tuple(str(item) for item in orientation.get("information_gaps") or ()),
            entity_attention=(),
            relationship_focus=(),
            temporal_focus=orientation.get("temporal_focus", "current"),  # type: ignore[arg-type]
            breadth_preference=orientation.get("breadth_preference", "broad"),  # type: ignore[arg-type]
        )
        return self._storyteller_service().prepare_assessment_context(
            orientation_obj,
            bundle,
            inference_id=inference_id,
        )

    def finalize_storyteller_assessment(
        self,
        *,
        hg_scene_id: str,
        hg_round_id: str,
        inference_id: str,
        orientation: dict[str, Any],
        bundle: dict[str, Any],
        assessment_result: dict[str, Any],
        orientation_inference_id: str,
        assessment_inference_id: str,
        follow_up_request_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        fixture = self.store.require(hg_scene_id)
        rnd = self._require_round(fixture, hg_round_id)
        orientation_obj = StorytellerOrientationAssessment(
            orientation_id=str(orientation["orientation_id"]),
            hg_round_id=str(orientation["hg_round_id"]),
            turn_index=int(orientation.get("turn_index", 0)),
            trigger=orientation.get("trigger", "round_start"),  # type: ignore[arg-type]
            information_gaps=tuple(str(item) for item in orientation.get("information_gaps") or ()),
            entity_attention=(),
            relationship_focus=(),
            temporal_focus=orientation.get("temporal_focus", "current"),  # type: ignore[arg-type]
            breadth_preference=orientation.get("breadth_preference", "broad"),  # type: ignore[arg-type]
        )
        return self._storyteller_service().finalize_assessment(
            fixture,
            rnd,
            orientation=orientation_obj,
            bundle=bundle,
            assessment_result=assessment_result,
            orientation_inference_id=orientation_inference_id,
            assessment_inference_id=assessment_inference_id,
            follow_up_request_ids=tuple(follow_up_request_ids or ()),
        )

    def validate_director_decision(
        self, req: DirectorDecisionValidationRequest
    ) -> DirectorDecisionResult:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        available = self._available_actors(fixture, rnd)
        current_snapshot_id = self._eligibility_snapshot_id(rnd)
        if req.eligibility_snapshot_id and req.eligibility_snapshot_id != current_snapshot_id:
            return DirectorDecisionResult(
                accepted=False,
                validation_class="continuity_anchor",
                reason=(
                    f"stale eligibility snapshot: expected {current_snapshot_id}, "
                    f"got {req.eligibility_snapshot_id}"
                ),
                retryable=False,
            )

        raw = req.raw_model_output
        if raw is None:
            raw = json.dumps(req.proposed_decision, ensure_ascii=False)

        parsed, parse_err = parse_director_decision(
            raw,
            participant_names=list(fixture.cast),
            available_actors=available,
        )
        if parse_err or parsed is None:
            proposed_actor = str(
                req.proposed_decision.get("next_actor", "") or ""
            ).strip()
            if (
                parse_err.startswith("Invalid next_actor:")
                and proposed_actor in fixture.cast
                and proposed_actor not in available
            ):
                exclusion = self._exclusion_reason(fixture, rnd, proposed_actor)
                return DirectorDecisionResult(
                    accepted=False,
                    validation_class="domain_rule",
                    reason=(
                        f"Director selected ineligible actor {proposed_actor}"
                        + (f" ({exclusion})" if exclusion else "")
                        + f"; eligible: {', '.join(available) or 'none'}"
                    ),
                    retryable=True,
                )
            return DirectorDecisionResult(
                accepted=False,
                validation_class="parse_error",
                reason=parse_err or "parse failed",
                retryable=True,
            )

        parsed = self._normalize_director_auxiliary_fields(fixture, parsed)

        if bool(parsed.get("end_round")):
            return DirectorDecisionResult(
                accepted=True,
                validation_class="accepted",
                reason="",
                retryable=False,
                normalized_decision=dict(parsed),
                selected_character_id=None,
            )

        next_actor = str(parsed.get("next_actor", "") or "").strip()
        if not next_actor:
            return DirectorDecisionResult(
                accepted=False,
                validation_class="domain_rule",
                reason="Director decision must select next_actor or set end_round",
                retryable=True,
                normalized_decision=dict(parsed),
            )
        if next_actor not in available:
            exclusion = self._exclusion_reason(fixture, rnd, next_actor)
            return DirectorDecisionResult(
                accepted=False,
                validation_class="domain_rule",
                reason=(
                    f"Director selected ineligible actor {next_actor}"
                    + (f" ({exclusion})" if exclusion else "")
                    + f"; eligible: {', '.join(available) or 'none'}"
                ),
                retryable=True,
                normalized_decision=dict(parsed),
            )

        constraint = str(req.director_constraint_actor or "").strip()
        if (
            constraint
            and constraint in available
            and not req.continuation_c2_skip
            and next_actor != constraint
        ):
            return DirectorDecisionResult(
                accepted=False,
                validation_class="domain_rule",
                reason=(
                    f"Director selected {next_actor} but participation constraint "
                    f"requires {constraint}"
                ),
                retryable=True,
                normalized_decision=dict(parsed),
            )

        return DirectorDecisionResult(
            accepted=True,
            validation_class="accepted",
            reason="",
            retryable=False,
            normalized_decision=dict(parsed),
            selected_character_id=next_actor,
        )

    def validate_move(self, req: ValidationRequest) -> ValidationResponse:
        fixture = self.store.require(req.hg_scene_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None

        raw = req.raw_model_output
        if raw is None:
            raw = json.dumps(req.proposed_move, ensure_ascii=False)

        parsed, parse_err = parse_character_move(raw)
        if parse_err or parsed is None:
            return ValidationResponse(
                accepted=False,
                validation_class="parse_error",
                reason=parse_err or "parse failed",
                retryable=True,
            )

        move_dict = dict(parsed)
        content = legacy_move_text_for_validation(move_dict)
        is_valid, reason = validate_bot_response_for_runtime(
            content=content,
            speaker=req.character_id,
            move=move_dict,
            scene_state=mgr.scene_state.to_dict(),
            continuity_manager=mgr,
        )
        if not is_valid:
            return ValidationResponse(
                accepted=False,
                validation_class="domain_rule",
                reason=reason,
                retryable=True,
                normalized_move=move_dict,
            )

        return ValidationResponse(
            accepted=True,
            validation_class="accepted",
            reason="",
            retryable=False,
            normalized_move=move_dict,
        )

    def commit_move(self, req: CommitRequest) -> CommitResponse:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        mgr = fixture.manager

        repository = self.store
        dedup_key: str | None = None
        if isinstance(repository, SessionRepository):
            dedup_key = repository.commit_dedup_key(
                hg_scene_id=req.hg_scene_id,
                inference_id=req.inference_id,
                expected_turn_index=req.expected_turn_index,
                character_id=req.character_id,
                validated_move=dict(req.validated_move),
                director_decision=dict(req.director_decision),
            )
            existing = repository.get_commit_dedup(dedup_key)
            if existing is not None:
                return existing.response

        if mgr.turn_counter != req.expected_turn_index:
            return CommitResponse(
                committed=False,
                continuity_turn_index=None,
                domain_commit_id=None,
                hg_scene_id=req.hg_scene_id,
                inference_id=req.inference_id,
                reason=(
                    f"continuity anchor mismatch: expected {req.expected_turn_index}, "
                    f"actual {mgr.turn_counter}"
                ),
            )

        others = [c for c in fixture.cast if c != req.character_id]
        director_decision = self._normalize_director_auxiliary_fields(
            fixture, dict(req.director_decision)
        )
        move = dict(req.validated_move)
        if issue240_semantic_evaluation_enabled():
            move = normalize_issue240_semantic_evaluation_for_continuity(move)

        manager_snapshot: dict[str, Any] | None = None
        round_snapshot: dict[str, Any] | None = None
        host_snapshot: dict[str, Any] | None = None
        if isinstance(repository, SessionRepository):
            manager_snapshot = repository.snapshot_manager(fixture)
            round_snapshot = {
                "director_decision": rnd.director_decision,
                "committed_character_id": rnd.committed_character_id,
                "committed_move": copy.deepcopy(rnd.committed_move)
                if rnd.committed_move is not None
                else None,
                "domain_commit_id": rnd.domain_commit_id,
                "continuity_turn_index": rnd.continuity_turn_index,
                "actors_used_this_round": list(rnd.actors_used_this_round),
                "character_turns": copy.deepcopy(rnd.character_turns),
                "spotlight_history": list(rnd.spotlight_history),
                "eligibility_epoch": rnd.eligibility_epoch,
            }
            host_snapshot = {
                "committed_move_count": fixture.committed_move_count,
                "commit_ids": list(fixture.commit_ids),
            }

        mgr.process_turn(
            acting_character=req.character_id,
            move=move,
            director_decision=director_decision,
            other_characters=others,
        )
        char_snapshot = (
            self._memory_service().snapshot_character_states(fixture)
            if self._memory_service() is not None
            else snapshot_character_states(fixture)
        )
        memory_service = self._memory_service()
        if memory_service is not None:
            memory_service.write_character_turn_memory(
                fixture,
                acting_character=req.character_id,
                move=move,
                director_decision=director_decision,
            )
        else:
            apply_character_turn_memory(
                fixture,
                acting_character=req.character_id,
                move=move,
                director_decision=director_decision,
            )
        after_turn = mgr.turn_counter
        commit_id = f"hg-commit-{uuid.uuid4()}"
        fixture.committed_move_count += 1
        fixture.commit_ids.append(commit_id)
        rnd.director_decision = director_decision
        rnd.committed_character_id = req.character_id
        rnd.committed_move = dict(req.validated_move)
        rnd.domain_commit_id = commit_id
        rnd.continuity_turn_index = after_turn
        rnd.actors_used_this_round.append(req.character_id)
        rnd.character_turns.append(
            CharacterTurnRecord(
                character_id=req.character_id,
                committed_move=dict(req.validated_move),
                domain_commit_id=commit_id,
                continuity_turn_index=after_turn,
                director_decision=director_decision,
            )
        )
        rnd.spotlight_history.append(req.character_id)
        rnd.eligibility_epoch += 1
        storyteller_invalidation_reason = self._invalidate_storyteller_package_for_round(
            rnd,
            reason="authoritative_commit",
        )

        if isinstance(repository, SessionRepository):
            append_history_entry(
                fixture.rp_history,
                kind="committed_turn",
                content=summarize_committed_move(dict(req.validated_move)),
                hg_round_id=req.hg_round_id,
                domain_commit_id=commit_id,
                actor_id=req.character_id,
                metadata={
                    "continuity_turn_index": after_turn,
                    "structured_move": dict(req.validated_move),
                },
            )

        response = CommitResponse(
            committed=True,
            continuity_turn_index=after_turn,
            domain_commit_id=commit_id,
            hg_scene_id=req.hg_scene_id,
            inference_id=req.inference_id,
            storyteller_invalidation_reason=storyteller_invalidation_reason,
        )
        if isinstance(repository, SessionRepository) and dedup_key is not None:
            repository.record_commit_dedup(
                dedup_key,
                CommitDedupRecord(
                    domain_commit_id=commit_id,
                    continuity_turn_index=after_turn,
                    response=response,
                ),
                fixture,
            )

        if hasattr(repository, "persist"):
            try:
                repository.persist(fixture)
            except PersistenceError as exc:
                if isinstance(repository, SessionRepository) and manager_snapshot is not None:
                    repository.restore_manager(fixture, manager_snapshot)
                    if memory_service is not None:
                        memory_service.restore_character_states(fixture, char_snapshot)
                    else:
                        restore_character_states(fixture, char_snapshot)
                    if round_snapshot is not None:
                        rnd.director_decision = round_snapshot["director_decision"]
                        rnd.committed_character_id = round_snapshot["committed_character_id"]
                        rnd.committed_move = round_snapshot["committed_move"]
                        rnd.domain_commit_id = round_snapshot["domain_commit_id"]
                        rnd.continuity_turn_index = round_snapshot["continuity_turn_index"]
                        rnd.actors_used_this_round = round_snapshot["actors_used_this_round"]
                        rnd.character_turns = round_snapshot["character_turns"]
                        rnd.spotlight_history = round_snapshot["spotlight_history"]
                        rnd.eligibility_epoch = round_snapshot["eligibility_epoch"]
                    if host_snapshot is not None:
                        fixture.committed_move_count = host_snapshot["committed_move_count"]
                        fixture.commit_ids = host_snapshot["commit_ids"]
                    if dedup_key is not None:
                        fixture.commit_dedup_index.pop(dedup_key, None)
                        repository._commit_dedup.pop(dedup_key, None)
                return CommitResponse(
                    committed=False,
                    continuity_turn_index=None,
                    domain_commit_id=None,
                    hg_scene_id=req.hg_scene_id,
                    inference_id=req.inference_id,
                    reason=str(exc),
                )
            knowledge_service = self._knowledge_service()
            if knowledge_service is not None:
                knowledge_service.promote_after_commit(
                    fixture,
                    source_domain_commit_id=commit_id,
                )
        return response

    def set_user_profile_fact(self, req: UserProfileSetRequest) -> dict[str, Any]:
        fixture = self.store.require(req.hg_session_id)
        knowledge_service = self._knowledge_service()
        if knowledge_service is None:
            raise ValueError("user profile writes require SessionRepository-backed knowledge store")
        return knowledge_service.write_user_profile(
            fixture,
            profile_key=req.profile_key,
            content=req.content,
            user_persona_id=req.user_persona_id,
        )

    def record_uncommitted_proposal(self, hg_scene_id: str) -> None:
        """Explicit no-op documenting that proposals do not mutate continuity."""
        self.store.require(hg_scene_id)

    def prepare_opening_context(
        self, req: OpeningContextPrepareRequest
    ) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_session_id)
        opening_entry_id = f"opening-{req.hg_session_id}"
        if any(
            item.get("entry_id") == opening_entry_id or item.get("kind") == "opening"
            for item in fixture.rp_history
        ):
            raise ValueError("opening presentation already materialized")

        mgr = fixture.manager
        assert mgr.scene_state is not None
        hg_scene_id = fixture.hg_scene_id
        hg_round_id = "opening-bootstrap"
        manifest_id = f"manifest-opening-{req.inference_id}"
        snapshot = fixture.setup_snapshot or {}
        scene_template = dict(snapshot.get("scene_template") or {})
        premise = str(
            scene_template.get("premise")
            or getattr(mgr.scene_state, "opening_description", "")
            or ""
        ).strip()

        auth_projections = project_authoritative_context(
            fixture,
            role="narrator",
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
        )
        contributions: list[PromptContribution] = list(
            self._auth_contributions_to_prompt(manifest_id, auth_projections)
        )

        if premise:
            contributions.append(
                PromptContribution(
                    contribution_id=f"{manifest_id}-scene-reference",
                    source_kind="scene_reference",
                    authority_class="authoritative",
                    knowledge_ids=(f"template:{scene_template.get('template_id', 'scene')}",),
                    priority=8,
                    content=f"Scene premise (authoritative): {premise}",
                    provenance={
                        "hg_scene_id": hg_scene_id,
                        "template_id": scene_template.get("template_id"),
                    },
                )
            )

        profile_lines: list[str] = []
        cards = dict(snapshot.get("character_cards") or {})
        for display_name in fixture.cast:
            card = None
            file_id = fixture.character_file_ids.get(display_name)
            if file_id and file_id in cards:
                card = cards[file_id]
            if not card:
                continue
            description = str(card.get("description", "")).strip()
            personality = str(card.get("personality", "")).strip()
            profile_lines.append(
                f"- {display_name}: {description}"
                + (f" Personality: {personality}" if personality else "")
            )
        if profile_lines:
            contributions.append(
                PromptContribution(
                    contribution_id=f"{manifest_id}-character-profiles",
                    source_kind="character_profile",
                    authority_class="authoritative",
                    knowledge_ids=tuple(f"profile:{name}" for name in fixture.cast),
                    priority=10,
                    content="Character profiles (authoritative setup):\n" + "\n".join(profile_lines),
                    provenance={"cast": list(fixture.cast)},
                )
            )

        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-instruction",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"inference:{req.inference_id}",),
                priority=30,
                content=build_opening_generation_instruction(
                    present_characters=list(fixture.cast),
                    premise=premise,
                ),
                provenance={"inference_id": req.inference_id, "role": "opening"},
            )
        )
        return PromptContributionManifest(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=hg_scene_id,
            hg_round_id=hg_round_id,
            role="opening",
            character_id=None,
            turn_index=0,
            attempt_index=0,
            contributions=tuple(contributions),
        )

    def persist_opening_presentation(self, req: OpeningPersistRequest) -> dict[str, Any]:
        fixture = self.store.require(req.hg_session_id)
        entry_id = f"opening-{req.hg_session_id}"
        existing = next(
            (item for item in fixture.rp_history if item.get("entry_id") == entry_id),
            None,
        )
        if existing is not None:
            return dict(existing)

        content = str(req.presentation_text or "").strip()
        if not content:
            raise ValueError("opening presentation text is required")

        snapshot = fixture.setup_snapshot or {}
        opening_meta = dict(snapshot.get("opening") or {})
        opening_meta.update(
            {
                "mode": "generated",
                "inference_id": req.inference_id,
                "manifest_id": req.manifest_id,
            }
        )
        entry = append_history_entry(
            fixture.rp_history,
            kind="opening",
            content=content,
            entry_id=entry_id,
            presentation_status="failed" if req.presentation_failed else "rendered",
            metadata={"opening": True, **opening_meta},
        )
        if isinstance(self.store, SessionRepository):
            self.store.persist(fixture)
        return entry

    def prepare_narrator_context(
        self, req: NarratorContextPrepareRequest
    ) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        turn_record = next(
            (turn for turn in rnd.character_turns if turn.domain_commit_id == req.domain_commit_id),
            None,
        )
        if turn_record is None:
            raise ValueError(
                f"narrator context requires a committed move for domain_commit_id "
                f"{req.domain_commit_id}"
            )
        if turn_record.continuity_turn_index != req.continuity_turn_index:
            raise ValueError(
                f"continuity_turn_index mismatch: expected {turn_record.continuity_turn_index}, "
                f"got {req.continuity_turn_index}"
            )
        if turn_record.character_id != req.character_id:
            raise ValueError(
                f"character_id mismatch: expected {turn_record.character_id}, "
                f"got {req.character_id}"
            )

        mgr = fixture.manager
        assert mgr.scene_state is not None
        manifest_id = f"manifest-narrator-{req.inference_id}-{req.attempt_index}"
        present_labels = list(
            getattr(mgr.scene_state, "present_characters", None) or fixture.cast
        )
        director_decision = dict(turn_record.director_decision)
        environment_event = str(director_decision.get("environment_event", "") or "")
        narrate_move = redact_structured_move_for_orchestration(
            dict(turn_record.committed_move),
            present_characters=present_labels,
        )
        auth_projections = project_authoritative_context(
            fixture,
            role="narrator",
            character_id=req.character_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            continuity_turn_index=turn_record.continuity_turn_index,
        )
        scene_context = next(
            (proj.content for proj in auth_projections if proj.source_kind == "scene_state"),
            (
                f"Location: {mgr.scene_state.location or 'unknown'}. "
                f"Present: {', '.join(present_labels)}. "
                f"Continuity turn counter after commit: {turn_record.continuity_turn_index}."
            ),
        )
        render_instruction = build_narrator_render_prompt(
            char_name=req.character_id,
            action="",
            dialogue="",
            environment_event=environment_event,
            scene_context=scene_context,
            structured_move=narrate_move,
        )
        committed_move_json = json.dumps(narrate_move, ensure_ascii=False, indent=2)
        contributions: list[PromptContribution] = list(
            self._auth_contributions_to_prompt(manifest_id, auth_projections)
        )
        contributions.extend(
            self._storyteller_contributions_for_role(
                fixture,
                rnd,
                manifest_id=manifest_id,
                consumer_target="narrator",
            )
        )
        contributions.extend(
            (
            PromptContribution(
                contribution_id=f"{manifest_id}-committed-move",
                source_kind="committed_move",
                authority_class="authoritative",
                knowledge_ids=(f"commit:{req.domain_commit_id}",),
                priority=20,
                content=(
                    f"Committed character move for {req.character_id} "
                    f"(domain_commit_id={req.domain_commit_id}):\n{committed_move_json}"
                ),
                provenance={
                    "character_id": req.character_id,
                    "domain_commit_id": req.domain_commit_id,
                    "visibility": "presentation",
                },
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-director-decision",
                source_kind="director_decision",
                authority_class="derived",
                knowledge_ids=(f"round:{req.hg_round_id}",),
                priority=25,
                content=(
                    "Accepted director decision for this round: "
                    f"{json.dumps(director_decision, ensure_ascii=False)}"
                ),
                provenance={
                    "hg_round_id": req.hg_round_id,
                    "visibility": "orchestration_projection",
                },
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-instruction",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"inference:{req.inference_id}",),
                priority=30,
                content=render_instruction,
                provenance={"inference_id": req.inference_id, "role": "narrator"},
            ),
            )
        )
        correction = req.correction_context
        if isinstance(correction, dict) and correction:
            contributions.insert(
                -1,
                PromptContribution(
                    contribution_id=f"{manifest_id}-semantic-correction",
                    source_kind="semantic_correction",
                    authority_class="suggestive",
                    knowledge_ids=(
                        str(correction.get("evaluation_pass_id") or req.inference_id),
                    ),
                    priority=29,
                    content=json.dumps(correction, ensure_ascii=False, indent=2),
                    provenance={
                        "inference_id": req.inference_id,
                        "visibility": "orchestration_only",
                        "attempt_index": req.attempt_index,
                    },
                ),
            )
        return PromptContributionManifest(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            role="narrator",
            character_id=req.character_id,
            turn_index=rnd.turn_index,
            attempt_index=req.attempt_index,
            contributions=contributions,
        )

    def prepare_narrator_semantic_qa_context(
        self, req: NarratorSemanticQaContextPrepareRequest
    ) -> SemanticQaContextPrepareResponse:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        turn_record = next(
            (turn for turn in rnd.character_turns if turn.domain_commit_id == req.domain_commit_id),
            None,
        )
        if turn_record is None:
            raise ValueError(
                f"narrator semantic QA requires committed move for domain_commit_id "
                f"{req.domain_commit_id}"
            )
        if turn_record.continuity_turn_index != req.continuity_turn_index:
            raise ValueError(
                f"continuity_turn_index mismatch: expected {turn_record.continuity_turn_index}, "
                f"got {req.continuity_turn_index}"
            )
        if turn_record.character_id != req.character_id:
            raise ValueError(
                f"character_id mismatch: expected {turn_record.character_id}, "
                f"got {req.character_id}"
            )

        manifest_id = f"manifest-narrator-semantic-qa-{req.evaluation_pass_id}"
        role_contributions, authority_refs, candidate_package = (
            prepare_narrator_semantic_qa_context(
                fixture,
                rnd,
                req,
                auth_contributions_fn=self._auth_contributions_to_prompt,
            )
        )
        return build_narrator_semantic_qa_context_response(
            manifest_id=manifest_id,
            evaluation_pass_id=req.evaluation_pass_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            turn_index=rnd.turn_index,
            character_id=req.character_id,
            role_contributions=role_contributions,
            authority_references=authority_refs,
            candidate_package=candidate_package,
        )

    def validate_narrator_presentation(
        self, req: NarratorPresentationValidationRequest
    ) -> NarratorPresentationValidationResponse:
        fixture = self.store.require(req.hg_scene_id)
        structured_move: dict[str, Any] | None = None
        committed = next(
            (
                item
                for item in reversed(fixture.rp_history)
                if item.get("kind") == "committed_turn"
                and item.get("domain_commit_id") == req.domain_commit_id
            ),
            None,
        )
        if committed is not None:
            meta = dict(committed.get("metadata") or {})
            move = meta.get("structured_move")
            if isinstance(move, dict):
                structured_move = move
        if structured_move is None:
            for rnd in fixture.rounds:
                turn_record = next(
                    (
                        turn
                        for turn in rnd.character_turns
                        if turn.domain_commit_id == req.domain_commit_id
                    ),
                    None,
                )
                if turn_record is not None:
                    structured_move = dict(turn_record.committed_move)
                    break
        if structured_move is None:
            return NarratorPresentationValidationResponse(
                accepted=False,
                validation_class="structural",
                reason=(
                    f"missing committed move for domain_commit_id "
                    f"{req.domain_commit_id}"
                ),
                retryable=False,
            )
        result = validate_narrator_presentation_rules(
            structured_move=structured_move,
            presentation_text=req.presentation_text,
        )
        return NarratorPresentationValidationResponse(
            accepted=result.accepted,
            validation_class=result.validation_class,
            reason=result.reason,
            retryable=result.retryable,
        )
