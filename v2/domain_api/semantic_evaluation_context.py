"""Read-only semantic evaluation context for Character pre-publication evaluation (#19)."""

from __future__ import annotations

import json
from typing import Any

from .continuity_context_projector import project_authoritative_context
from .character_conversation_projection import project_character_conversation_for_manifest
from .context_substrate import auth_projections_to_contributions
from .contract import PromptContribution, SemanticEvaluationContextPrepareRequest
from perceptual_visibility_legacy import perceptual_visibility_record_from_entry_metadata

from .player_action_completion_authority import (
    PLAYER_ACTION_COMPLETION_GUARDRAIL_ID,
    merge_player_action_completion_authority_references,
)
from .player_authorship_authority import (
    PLAYER_AUTHORSHIP_GUARDRAIL_ID,
    merge_player_authorship_authority_references,
)
from .character_perceptual_inventory import build_character_perceptual_inventory_refs
from .player_authorship_authority import CHARACTER_PERCEPTUAL_GROUNDING_DISCIPLINE
from .viewer_player_perception import assemble_viewer_player_perception_for_session

PERCEPTION_FACT_PLAYER_INTERNAL_ENTITLEMENT = "perception_fact:player_internal_entitlement"


def project_perception_entitlement_authority_references(
    fixture: Any,
    *,
    character_id: str,
) -> list[dict[str, Any]]:
    """#155 perception/entitlement refs citeable for hard R14 findings."""
    refs: list[dict[str, Any]] = [
        {
            "ref_id": PERCEPTION_FACT_PLAYER_INTERNAL_ENTITLEMENT,
            "kind": "perception_fact",
            "label": "Player internal-unit entitlement (#155)",
            "text": (
                "Per #155 perceptual visibility: Player decomposition units with kind "
                "'internal' are never perceivable by other Characters. They may establish "
                "Player authorship (R02b) but not viewer entitlement (R14). Hard R14 "
                "findings for established-but-not-entitled Player facts must cite "
                "perception_fact:entitlement:{entry_id}:{unit_id} when present."
            ),
        }
    ]
    mgr = getattr(fixture, "manager", None)
    present = list(
        getattr(getattr(mgr, "scene_state", None), "present_characters", None)
        or getattr(fixture, "cast", None)
        or []
    )
    history = list(getattr(fixture, "rp_history", None) or [])
    for entry in history:
        if str(entry.get("kind") or "") != "user":
            continue
        entry_id = str(entry.get("entry_id") or "").strip()
        if not entry_id:
            continue
        assembly = assemble_viewer_player_perception_for_session(
            fixture,
            entry,
            viewer_character=character_id,
            present_characters=present,
        )
        unit_text: dict[str, str] = {}
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        record, _ = perceptual_visibility_record_from_entry_metadata(metadata)
        if record is not None:
            for unit in record.units:
                unit_text[str(unit.unit_id)] = str(unit.text or "").strip()
        seen_unit_ids: set[str] = set()
        for unit_id in assembly.excluded_unit_ids:
            if unit_id in seen_unit_ids:
                continue
            seen_unit_ids.add(unit_id)
            reason = str(assembly.exclusion_reasons.get(unit_id) or "recipient_ineligible")
            snippet = unit_text.get(unit_id, "")
            refs.append(
                {
                    "ref_id": f"perception_fact:entitlement:{entry_id}:{unit_id}",
                    "kind": "perception_fact",
                    "label": f"Perception entitlement ({character_id} excluded: {unit_id})",
                    "text": (
                        f"Viewer Character {character_id} is NOT entitled to perceive "
                        f"Player unit {unit_id} from entry {entry_id} "
                        f"(exclusion: {reason})."
                        + (f" Unit: {snippet}" if snippet else "")
                    ),
                }
            )
    return refs


def build_authority_references(
    fixture: Any,
    *,
    character_id: str,
    hg_round_id: str,
) -> list[dict[str, Any]]:
    """Stable authority references the semantic evaluator may cite for hard findings."""
    refs: list[dict[str, Any]] = []
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
    refs.extend(
        project_perception_entitlement_authority_references(
            fixture,
            character_id=character_id,
        )
    )
    inventory_refs = build_character_perceptual_inventory_refs(
        fixture,
        character_id=character_id,
        hg_round_id=hg_round_id,
    )
    refs.extend(inventory_refs)
    refs = merge_player_authorship_authority_references(refs, fixture)
    return merge_player_action_completion_authority_references(refs)


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
                "Evaluate the candidate for R02b Player authorship (is an asserted Player fact "
                "authoritatively established?), R11 repetition/stagnation, R12 character "
                "fidelity, R14 knowledge/perception entitlement (may this Character know/use an "
                "otherwise-established fact?), R15 binding continuity, R16 player action "
                "completion (does the candidate represent a Player action or positional state "
                "as accomplished without sufficient authoritative support?). "
                "Unsupported objective Player assertion/sensation/amplification → R02b hard with "
                "guardrail:player_authorship; established-but-not-entitled → R14 hard with "
                "perception_fact:entitlement:* or perception_fact:player_internal_entitlement "
                "(not guardrail:player_authorship alone). "
                "R02b perceptual grounding: Character private/scenario knowledge cannot serve as "
                "sensory evidence. Player physical/physiological/emotional-display claims require "
                "support from perception_fact:authorized_inventory:*, perception_fact:entitled:*, "
                "grounding:*, or established player_fact:* observable sources in the references "
                "block. Subjective grammar does not cure missing substrate. Fallible interpretation "
                "from real entitled perceptual evidence remains allowed. "
                f"{CHARACTER_PERCEPTUAL_GROUNDING_DISCIPLINE} "
                "Unsupported assumed Player acceptance/entry/agreement/positional completion "
                "→ R16 hard with guardrail:player_action_completion and cite offending beat "
                "evidence; invitation/permission/threat/attempt without established completion "
                "must not be treated as accomplished Player movement. "
                "Output only JSON matching schema hg_semantic_evaluation_result_v1. "
                "Use overall_result pass|reject_soft|reject_hard only. "
                "Hard findings require a valid authority ref_id from the references block. "
                "Do not fabricate player_fact:* refs for unsupported assertions; cite the "
                "guardrail and inventory absence. Do not supply replacement RP prose."
            ),
            provenance={"evaluation_pass_id": req.evaluation_pass_id},
        )
    )
    candidate_package = {
        "candidate_move": dict(req.candidate_move),
        "raw_model_output": req.raw_model_output,
    }
    return contributions, authority_refs, candidate_package
