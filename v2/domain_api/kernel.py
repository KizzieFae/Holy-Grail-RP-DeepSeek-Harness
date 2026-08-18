"""Authoritative Holy Grail domain kernel for the V2 boundary prototype."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

_RP_APP = Path(__file__).resolve().parents[2] / "autogen_rp" / "python" / "rp_app"
if str(_RP_APP) not in sys.path:
    sys.path.insert(0, str(_RP_APP))

from character_move_adapters import legacy_move_text_for_validation  # noqa: E402
from perception_audibility_structured import redact_structured_move_for_orchestration  # noqa: E402
from prompt_builders import build_narrator_render_prompt  # noqa: E402
from response_validation import validate_bot_response  # noqa: E402
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

from .contract import (  # noqa: E402
    CommitRequest,
    CommitResponse,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionResult,
    DirectorDecisionValidationRequest,
    EligibleActorsRequest,
    EligibleActorsResponse,
    EligibleActorEntry,
    NarratorContextPrepareRequest,
    ParticipationDecision,
    ParticipationDecisionRequest,
    PromptContribution,
    PromptContributionManifest,
    RoundStartRequest,
    RoundStartResponse,
    SceneStateSnapshot,
    ValidationRequest,
    ValidationResponse,
)
from .fixture_store import CharacterTurnRecord, FixtureStore, RoundFixture, SceneFixture  # noqa: E402
from .participation_policy import evaluate_participation_policy  # noqa: E402

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
    def __init__(self, store: FixtureStore | None = None) -> None:
        self.store = store or FixtureStore()

    def create_scene(self, **kwargs: Any) -> SceneFixture:
        return self.store.create_scene(**kwargs)

    def scene_snapshot(self, hg_scene_id: str) -> SceneStateSnapshot:
        fixture = self.store.require(hg_scene_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        present = tuple(
            str(name)
            for name in (getattr(mgr.scene_state, "present_characters", None) or fixture.cast)
        )
        return SceneStateSnapshot(
            hg_scene_id=hg_scene_id,
            location=str(mgr.scene_state.location or ""),
            turn_counter=int(mgr.turn_counter),
            present_characters=present,
            committed_move_count=fixture.committed_move_count,
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

    def _require_round(self, fixture: SceneFixture, hg_round_id: str) -> RoundFixture:
        for rnd in fixture.rounds:
            if rnd.hg_round_id == hg_round_id:
                return rnd
        raise KeyError(f"unknown hg_round_id: {hg_round_id}")

    def _eligibility_snapshot_id(self, rnd: RoundFixture) -> str:
        return f"{rnd.hg_round_id}:{rnd.eligibility_epoch}"

    def _presence_status(self, fixture: SceneFixture, character_id: str) -> str:
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
        self, fixture: SceneFixture, rnd: RoundFixture, character_id: str
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
        return None

    def _eligibility_projection(
        self, fixture: SceneFixture, rnd: RoundFixture
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

    def _available_actors(self, fixture: SceneFixture, rnd: RoundFixture) -> list[str]:
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

    def prepare_director_context(
        self, req: DirectorContextPrepareRequest
    ) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        manifest_id = f"manifest-director-{req.inference_id}-{req.attempt_index}"
        location = str(mgr.scene_state.location or "unknown")
        present_labels = list(getattr(mgr.scene_state, "present_characters", None) or fixture.cast)
        offstage_labels = list(getattr(mgr.scene_state, "offstage_characters", None) or [])
        present = ", ".join(present_labels) if present_labels else "none"
        offstage = ", ".join(offstage_labels) if offstage_labels else "none"
        used = list(req.actors_used_this_round) or list(rnd.actors_used_this_round)
        available = self._available_actors(fixture, rnd)
        used_label = ", ".join(used) if used else "none"
        available_label = ", ".join(available) if available else "none"
        contributions = (
            PromptContribution(
                contribution_id=f"{manifest_id}-scene",
                source_kind="scene_state",
                authority_class="authoritative",
                knowledge_ids=(f"scene:{req.hg_scene_id}",),
                priority=10,
                content=(
                    f"Scene location: {location}. Present characters: {present}. "
                    f"Offstage characters: {offstage}. "
                    f"Continuity turn counter: {mgr.turn_counter}. "
                    f"Actors already used this round: {used_label}. "
                    f"Eligible actors: {available_label}."
                ),
                provenance={"hg_scene_id": req.hg_scene_id, "hg_round_id": req.hg_round_id},
            ),
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
                    "tension_shift."
                ),
                provenance={"inference_id": req.inference_id},
            ),
        )
        return PromptContributionManifest(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            role="director",
            character_id=None,
            turn_index=rnd.turn_index,
            attempt_index=req.attempt_index,
            contributions=contributions,
        )

    def prepare_context(self, req: ContextPrepareRequest) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        manifest_id = f"manifest-character-{req.inference_id}-{req.attempt_index}"
        location = str(mgr.scene_state.location or "unknown")
        present = ", ".join(fixture.cast)
        private_secret = fixture.character_private_secrets.get(req.character_id, "")
        contributions: list[PromptContribution] = [
            PromptContribution(
                contribution_id=f"{manifest_id}-scene",
                source_kind="scene_state",
                authority_class="authoritative",
                knowledge_ids=(f"scene:{req.hg_scene_id}",),
                priority=10,
                content=(
                    f"Scene location: {location}. Present characters: {present}. "
                    f"Continuity turn counter: {mgr.turn_counter}."
                ),
                provenance={
                    "hg_scene_id": req.hg_scene_id,
                    "hg_round_id": req.hg_round_id,
                    "turn_index": req.turn_index,
                },
            ),
        ]
        if rnd.character_turns:
            prior_lines = []
            for turn in rnd.character_turns:
                move_json = json.dumps(turn.committed_move, ensure_ascii=False)
                prior_lines.append(
                    f"- {turn.character_id} (commit {turn.domain_commit_id}): {move_json}"
                )
            contributions.append(
                PromptContribution(
                    contribution_id=f"{manifest_id}-continuity-summary",
                    source_kind="continuity_summary",
                    authority_class="authoritative",
                    knowledge_ids=tuple(
                        f"commit:{turn.domain_commit_id}" for turn in rnd.character_turns
                    ),
                    priority=15,
                    content=(
                        "Committed turns earlier in this round:\n" + "\n".join(prior_lines)
                    ),
                    provenance={
                        "hg_round_id": req.hg_round_id,
                        "visibility": "orchestration_projection",
                    },
                )
            )
        contributions.extend(
            (
            PromptContribution(
                contribution_id=f"{manifest_id}-character",
                source_kind="character_profile",
                authority_class="authoritative",
                knowledge_ids=(f"character:{req.character_id}",),
                priority=20,
                content=(
                    f"You are {req.character_id} ({req.role}). "
                    "Respond with a single JSON object: canonical character move v2."
                ),
                provenance={"character_id": req.character_id, "role": req.role},
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-character-private",
                source_kind="character_private",
                authority_class="authoritative",
                knowledge_ids=(f"character-private:{req.character_id}",),
                priority=25,
                content=f"Character-private knowledge for {req.character_id}: {private_secret}",
                provenance={"character_id": req.character_id, "visibility": "character_only"},
            ),
            PromptContribution(
                contribution_id=f"{manifest_id}-instruction",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"inference:{req.inference_id}",),
                priority=30,
                content=(
                    "Output only valid JSON for move_schema_version 2 with non-empty beats[], "
                    "motivation object, and semantic_evaluation."
                ),
                provenance={"inference_id": req.inference_id},
            ),
            )
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
            available_actors=list(fixture.cast),
        )
        if parse_err or parsed is None:
            return DirectorDecisionResult(
                accepted=False,
                validation_class="parse_error",
                reason=parse_err or "parse failed",
                retryable=True,
            )

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
        is_valid, reason = validate_bot_response(
            content=content,
            speaker=req.character_id,
            user_name="Player",
            chat_history=[],
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
        director_decision = dict(req.director_decision)
        move = dict(req.validated_move)
        if issue240_semantic_evaluation_enabled():
            move = normalize_issue240_semantic_evaluation_for_continuity(move)

        mgr.process_turn(
            acting_character=req.character_id,
            move=move,
            director_decision=director_decision,
            other_characters=others,
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

        return CommitResponse(
            committed=True,
            continuity_turn_index=after_turn,
            domain_commit_id=commit_id,
            hg_scene_id=req.hg_scene_id,
            inference_id=req.inference_id,
        )

    def record_uncommitted_proposal(self, hg_scene_id: str) -> None:
        """Explicit no-op documenting that proposals do not mutate continuity."""
        self.store.require(hg_scene_id)

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
        manifest_id = f"manifest-narrator-{req.inference_id}"
        location = str(mgr.scene_state.location or "unknown")
        present = ", ".join(fixture.cast)
        director_decision = dict(turn_record.director_decision)
        environment_event = str(director_decision.get("environment_event", "") or "")
        narrate_move = redact_structured_move_for_orchestration(
            dict(turn_record.committed_move),
            present_characters=list(fixture.cast),
        )
        scene_context = (
            f"Location: {location}. Present: {present}. "
            f"Continuity turn counter after commit: {turn_record.continuity_turn_index}."
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
        contributions = (
            PromptContribution(
                contribution_id=f"{manifest_id}-scene",
                source_kind="scene_state",
                authority_class="authoritative",
                knowledge_ids=(f"scene:{req.hg_scene_id}",),
                priority=10,
                content=scene_context,
                provenance={
                    "hg_scene_id": req.hg_scene_id,
                    "hg_round_id": req.hg_round_id,
                    "domain_commit_id": req.domain_commit_id,
                    "continuity_turn_index": req.continuity_turn_index,
                },
            ),
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
                authority_class="authoritative",
                knowledge_ids=(f"round:{req.hg_round_id}",),
                priority=25,
                content=(
                    "Accepted director decision for this round: "
                    f"{json.dumps(director_decision, ensure_ascii=False)}"
                ),
                provenance={"hg_round_id": req.hg_round_id},
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
        return PromptContributionManifest(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            hg_round_id=req.hg_round_id,
            role="narrator",
            character_id=req.character_id,
            turn_index=rnd.turn_index,
            attempt_index=0,
            contributions=contributions,
        )
