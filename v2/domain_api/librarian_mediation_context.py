"""Host-prepared Librarian mediation context for DSH inference (#34 S2a)."""

from __future__ import annotations

import json
from typing import Any

from .contract import PromptContribution
from .librarian_contract import KnowledgeAccessRequest, MediationCatalogItem


def build_mediation_manifest_contributions(
    request: KnowledgeAccessRequest,
    *,
    manifest_id: str,
    inference_id: str,
    catalog: tuple[MediationCatalogItem, ...],
    authoritative_snapshot_id: str,
) -> list[PromptContribution]:
    need = request.information_need
    envelope = request.visibility_envelope
    request_block = {
        "request_id": request.request_id,
        "consumer_role": request.consumer_role,
        "pipeline_stage": request.pipeline_stage,
        "focus_questions": list(need.focus_questions),
        "topics": list(need.topics),
        "entity_refs": [
            {
                "ref_kind": ref.ref_kind,
                "stable_ref": ref.stable_ref,
                "display_hint": ref.display_hint,
            }
            for ref in need.entity_refs
        ],
        "relationship_focus": [
            {
                "subject_ref": item.subject_ref,
                "object_ref": item.object_ref,
                "relationship_kind": item.relationship_kind,
            }
            for item in need.relationship_focus
        ],
        "temporal_orientation": need.temporal_orientation,
        "recall_breadth_preference": need.recall_breadth_preference,
    }
    envelope_block = {
        "viewer_role": envelope.viewer_role,
        "authority_ceiling_enforced": envelope.authority_ceiling_enforced,
        "viewer_character_id": envelope.viewer_character_id,
        "subject_character_id": envelope.subject_character_id,
        "session_template_id": envelope.session_template_id,
    }
    catalog_block = [
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
            "provenance": item.provenance,
        }
        for item in catalog
    ]
    contributions: list[PromptContribution] = [
        PromptContribution(
            contribution_id=f"{manifest_id}-request",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"librarian_request:{request.request_id}",),
            priority=10,
            content=(
                "KnowledgeAccessRequest (information plane only — not narrative direction):\n"
                f"{json.dumps(request_block, ensure_ascii=False, indent=2)}"
            ),
            provenance={
                "inference_id": inference_id,
                "request_id": request.request_id,
                "visibility": "orchestration_only",
            },
        ),
        PromptContribution(
            contribution_id=f"{manifest_id}-envelope",
            source_kind="active_constraints",
            authority_class="authoritative",
            knowledge_ids=(f"librarian_envelope:{request.request_id}",),
            priority=11,
            content=(
                "Host visibility/authority envelope (must not be widened by inference output):\n"
                f"{json.dumps(envelope_block, ensure_ascii=False, indent=2)}"
            ),
            provenance={
                "inference_id": inference_id,
                "authoritative_snapshot_id": authoritative_snapshot_id,
            },
        ),
        PromptContribution(
            contribution_id=f"{manifest_id}-catalog",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=tuple(item.source_id for item in catalog),
            priority=20,
            content=(
                "Eligible mediation catalog. Reference ONLY these source_id values. "
                "Select/rank by contextual information relevance to the focus questions — "
                "not token overlap alone, not narrative significance, not plot direction.\n"
                f"{json.dumps(catalog_block, ensure_ascii=False, indent=2)}"
            ),
            provenance={"inference_id": inference_id, "catalog_count": len(catalog_block)},
        ),
        PromptContribution(
            contribution_id=f"{manifest_id}-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"librarian_mediation:{request.request_id}",),
            priority=30,
            content=(
                "Return ONLY one JSON object matching schema "
                f"{json.dumps({'schema': 'hg_librarian_mediation_result_v1'})}. "
                "Use selected_items[].source_id from the catalog only. "
                "Do not introduce new source identities or authoritative facts. "
                "Synthesis entries must cite source_ids from the catalog. "
                "This is suggestive information mediation — not Storyteller narrative advice."
            ),
            provenance={"inference_id": inference_id},
        ),
    ]
    return contributions
