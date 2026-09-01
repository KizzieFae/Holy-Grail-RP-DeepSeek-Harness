"""Read-only semantic evaluation context for Character pre-publication evaluation (#19)."""

from __future__ import annotations

import json
from typing import Any

from .continuity_context_projector import project_authoritative_context
from .character_conversation_projection import project_character_conversation_for_manifest
from .context_substrate import auth_projections_to_contributions
from .contract import PromptContribution, SemanticEvaluationContextPrepareRequest

PLAYER_AGENCY_GUARDRAIL_ID = "guardrail:player_agency"


def _player_agency_guardrail() -> dict[str, Any]:
    return {
        "ref_id": PLAYER_AGENCY_GUARDRAIL_ID,
        "kind": "guardrail",
        "label": "Player agency",
        "text": (
            "Do not invent player dialogue, voluntary action, thoughts, emotions, "
            "intentions, decisions, or equivalent player-controlled behavior."
        ),
    }


def build_authority_references(
    fixture: Any,
    *,
    character_id: str,
    hg_round_id: str,
) -> list[dict[str, Any]]:
    """Stable authority references the semantic evaluator may cite for hard findings."""
    refs: list[dict[str, Any]] = [_player_agency_guardrail()]
    mgr = fixture.manager
    state = getattr(fixture, "character_states", {}).get(character_id)
    if state is not None:
        name = str(getattr(state, "name", "") or character_id)
        refs.append(
            {
                "ref_id": f"character_fact:{character_id}:identity",
                "kind": "character_fact",
                "label": f"Character identity ({character_id})",
                "text": f"Authoritative character identity/name: {name}",
            }
        )
    if mgr is not None and mgr.scene_state is not None:
        location = str(getattr(mgr.scene_state, "location", "") or "").strip()
        if location:
            refs.append(
                {
                    "ref_id": f"continuity_fact:scene:location",
                    "kind": "continuity_fact",
                    "label": "Scene location",
                    "text": f"Committed scene location: {location}",
                }
            )
        present = list(getattr(mgr.scene_state, "present_characters", None) or [])
        if present:
            refs.append(
                {
                    "ref_id": "perception_fact:scene:present_characters",
                    "kind": "perception_fact",
                    "label": "Present characters",
                    "text": f"Characters present in scene: {', '.join(present)}",
                }
            )
        constraints = getattr(mgr.scene_state, "character_presence_constraints", None) or {}
        if isinstance(constraints, dict):
            for char_name, constraint in constraints.items():
                refs.append(
                    {
                        "ref_id": f"continuity_fact:presence:{char_name}",
                        "kind": "continuity_fact",
                        "label": f"Presence constraint ({char_name})",
                        "text": f"{char_name} presence constraint: {constraint}",
                    }
                )
        slots = getattr(mgr.scene_state, "sleeping_surface_slots", None) or []
        if isinstance(slots, list) and slots:
            refs.append(
                {
                    "ref_id": "binding_fact:sleeping_surface_slots",
                    "kind": "binding_fact",
                    "label": "Sleeping surface slots",
                    "text": f"Authoritative sleeping surface slots: {', '.join(str(s) for s in slots)}",
                }
            )
    anchors = []
    if mgr is not None:
        try:
            anchors = list(
                mgr.get_relevant_canon_anchors(character_id, participants=fixture.cast, limit=8)
            )
        except (TypeError, AttributeError):
            anchors = []
    for index, anchor in enumerate(anchors):
        statement = str(getattr(anchor, "statement", "") or "").strip()
        if not statement:
            continue
        subject = str(getattr(anchor, "subject", "") or "canon")
        refs.append(
            {
                "ref_id": f"continuity_fact:canon:{index}",
                "kind": "continuity_fact",
                "label": f"Canon anchor ({subject})",
                "text": statement,
            }
        )
    refs.append(
        {
            "ref_id": "perception_fact:character_action_recipients",
            "kind": "perception_fact",
            "label": "Character action recipient contract",
            "text": (
                "Physical action beats use optional recipients.scope (default present). "
                "Concealed or restricted physical action must use restrictive recipients "
                "(directed/private with named characters), not default present. "
                "Speech beats use audibility and audience only."
            ),
        }
    )
    _ = hg_round_id
    return refs


def prepare_semantic_evaluation_context(
    fixture: Any,
    req: SemanticEvaluationContextPrepareRequest,
) -> tuple[list[PromptContribution], list[dict[str, Any]], dict[str, Any]]:
    manifest_id = f"manifest-semantic-eval-{req.evaluation_pass_id}"
    auth_projections = project_authoritative_context(
        fixture,
        role="character",
        character_id=req.character_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        turn_index=req.turn_index,
    )
    contributions: list[PromptContribution] = list(
        auth_projections_to_contributions(manifest_id, auth_projections)
    )
    transcript_content, trigger_content, conv_prov = project_character_conversation_for_manifest(
        fixture,
        character_id=req.character_id,
    )
    if transcript_content:
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-recent-scene-transcript",
                source_kind="recent_scene_transcript",
                authority_class="derived",
                knowledge_ids=(f"rp_history:transcript:{req.character_id}:{req.hg_round_id}",),
                priority=16,
                content=transcript_content,
                provenance={
                    "hg_round_id": req.hg_round_id,
                    "visibility": "character_viewer_projection",
                    **conv_prov,
                },
            )
        )
    if trigger_content:
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-user-turn-trigger",
                source_kind="user_turn_trigger",
                authority_class="derived",
                knowledge_ids=(f"rp_history:trigger:{req.character_id}:{req.hg_round_id}",),
                priority=17,
                content=trigger_content,
                provenance={
                    "hg_round_id": req.hg_round_id,
                    "visibility": "character_viewer_projection",
                    **conv_prov,
                },
            )
        )
    authority_refs = build_authority_references(
        fixture,
        character_id=req.character_id,
        hg_round_id=req.hg_round_id,
    )
    refs_block = json.dumps(authority_refs, ensure_ascii=False, indent=2)
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-authority-references",
            source_kind="active_constraints",
            authority_class="authoritative",
            knowledge_ids=tuple(ref["ref_id"] for ref in authority_refs),
            priority=18,
            content=(
                "Authoritative guardrails and facts (cite ref_id for hard findings):\n"
                f"{refs_block}"
            ),
            provenance={"evaluation_pass_id": req.evaluation_pass_id},
        )
    )
    candidate_json = json.dumps(req.candidate_move, ensure_ascii=False, indent=2)
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-candidate",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"candidate:{req.evaluation_pass_id}",),
            priority=25,
            content=(
                "Candidate Character move under evaluation (parsed/normalized JSON):\n"
                f"{candidate_json}"
            ),
            provenance={"evaluation_pass_id": req.evaluation_pass_id},
        )
    )
    if req.raw_model_output:
        contributions.append(
            PromptContribution(
                contribution_id=f"{manifest_id}-candidate-raw",
                source_kind="inference_instruction",
                authority_class="derived",
                knowledge_ids=(f"candidate_raw:{req.evaluation_pass_id}",),
                priority=26,
                content=f"Raw Character model output:\n{req.raw_model_output}",
                provenance={"evaluation_pass_id": req.evaluation_pass_id},
            )
        )
    contributions.append(
        PromptContribution(
            contribution_id=f"{manifest_id}-eval-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"semantic_eval:{req.evaluation_pass_id}",),
            priority=30,
            content=(
                "Evaluate the candidate for R02b player agency, R11 repetition/stagnation, "
                "R12 character fidelity, R14 knowledge/perception, R15 binding continuity. "
                "Output only JSON matching schema hg_semantic_evaluation_result_v1. "
                "Hard findings require a valid authority ref_id from the references block. "
                "Do not supply replacement RP prose."
            ),
            provenance={"evaluation_pass_id": req.evaluation_pass_id},
        )
    )
    candidate_package = {
        "candidate_move": dict(req.candidate_move),
        "raw_model_output": req.raw_model_output,
    }
    return contributions, authority_refs, candidate_package
