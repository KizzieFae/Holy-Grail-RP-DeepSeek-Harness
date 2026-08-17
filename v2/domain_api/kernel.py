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
from response_validation import validate_bot_response  # noqa: E402
from response_validation_parsing import parse_character_move  # noqa: E402

from .contract import (  # noqa: E402
    CommitRequest,
    CommitResponse,
    ContextPrepareRequest,
    PromptContribution,
    PromptContributionManifest,
    SceneStateSnapshot,
    ValidationRequest,
    ValidationResponse,
)
from .fixture_store import FixtureStore, SceneFixture  # noqa: E402

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

    def prepare_context(self, req: ContextPrepareRequest) -> PromptContributionManifest:
        fixture = self.store.require(req.hg_scene_id)
        mgr = fixture.manager
        assert mgr.scene_state is not None
        manifest_id = f"manifest-{req.inference_id}-{req.attempt_index}"
        location = str(mgr.scene_state.location or "unknown")
        present = ", ".join(fixture.cast)
        contributions = (
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
                    "turn_index": req.turn_index,
                },
            ),
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
        return PromptContributionManifest(
            manifest_id=manifest_id,
            inference_id=req.inference_id,
            hg_scene_id=req.hg_scene_id,
            character_id=req.character_id,
            turn_index=req.turn_index,
            attempt_index=req.attempt_index,
            contributions=contributions,
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
        next_actor = others[0] if others else req.character_id
        director_decision = {"next_actor": next_actor, "end_round": False, "reason": "prototype"}

        before_turn = mgr.turn_counter
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
