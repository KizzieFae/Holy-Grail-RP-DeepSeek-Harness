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
from response_validation_parsing import (  # noqa: E402
    parse_character_move,
    parse_director_decision,
)

from .contract import (  # noqa: E402
    CommitRequest,
    CommitResponse,
    ContextPrepareRequest,
    DirectorContextPrepareRequest,
    DirectorDecisionResult,
    DirectorDecisionValidationRequest,
    NarratorContextPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
    RoundStartRequest,
    RoundStartResponse,
    SceneStateSnapshot,
    ValidationRequest,
    ValidationResponse,
)
from .fixture_store import CharacterTurnRecord, FixtureStore, RoundFixture, SceneFixture  # noqa: E402

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


class DomainKernel:
    def __init__(self, store: FixtureStore | None = None) -> None:
        self.store = store or FixtureStore()

    def create_scene(self, **kwargs: Any) -> SceneFixture:
        return self.store.create_scene(**kwargs)

    def scene_snapshot(self, hg_scene_id: str) -> SceneStateSnapshot:
        fixture = self.store.require(hg_scene_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        return SceneStateSnapshot(
            hg_scene_id=hg_scene_id,
            location=str(mgr.scene_state.location or ""),
            turn_counter=int(mgr.turn_counter),
            present_characters=tuple(fixture.cast),
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

    def _available_actors(self, fixture: SceneFixture, rnd: RoundFixture) -> list[str]:
        used = set(rnd.actors_used_this_round)
        return [name for name in fixture.cast if name not in used]

    def prepare_director_context(
        self, req: DirectorContextPrepareRequest
    ) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_scene_id)
        rnd = self._require_round(fixture, req.hg_round_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        manifest_id = f"manifest-director-{req.inference_id}-{req.attempt_index}"
        location = str(mgr.scene_state.location or "unknown")
        present = ", ".join(fixture.cast)
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
                    f"Continuity turn counter: {mgr.turn_counter}. "
                    f"Actors already used this round: {used_label}. "
                    f"Available actors: {available_label}."
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

        raw = req.raw_model_output
        if raw is None:
            raw = json.dumps(req.proposed_decision, ensure_ascii=False)

        parsed, parse_err = parse_director_decision(
            raw,
            participant_names=list(fixture.cast),
            available_actors=available,
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
            return DirectorDecisionResult(
                accepted=False,
                validation_class="domain_rule",
                reason=(
                    f"Director selected unavailable actor {next_actor}; "
                    f"available: {', '.join(available) or 'none'}"
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

        mgr.process_turn(
            acting_character=req.character_id,
            move=dict(req.validated_move),
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
