"""Shared semantic-QA context/manifest assembly helpers (#25)."""

from __future__ import annotations

import json
from typing import Any

from domain_api.contract import PromptContribution, SemanticQaContextPrepareResponse

from domain.modules.authority_reference import validate_authority_references


def append_authority_references_contribution(
    contributions: list[PromptContribution],
    *,
    manifest_id: str,
    authority_references: list[dict[str, Any]],
    evaluation_pass_id: str,
    priority: int = 18,
) -> list[PromptContribution]:
    """Append a transport contribution listing citeable authority references."""
    refs_block = json.dumps(authority_references, ensure_ascii=False, indent=2)
    return [
        *contributions,
        PromptContribution(
            contribution_id=f"{manifest_id}-authority-references",
            source_kind="active_constraints",
            authority_class="authoritative",
            knowledge_ids=tuple(ref["ref_id"] for ref in authority_references),
            priority=priority,
            content=(
                "Authority references supplied for semantic QA (cite ref_id in findings):\n"
                f"{refs_block}"
            ),
            provenance={"evaluation_pass_id": evaluation_pass_id},
        ),
    ]


def append_candidate_package_contribution(
    contributions: list[PromptContribution],
    *,
    manifest_id: str,
    candidate_package: dict[str, Any],
    evaluation_pass_id: str,
    candidate_label: str = "Candidate under evaluation",
    priority: int = 25,
) -> list[PromptContribution]:
    """Append a transport contribution for the candidate payload metadata."""
    candidate_json = json.dumps(candidate_package, ensure_ascii=False, indent=2)
    return [
        *contributions,
        PromptContribution(
            contribution_id=f"{manifest_id}-candidate-package",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"candidate:{evaluation_pass_id}",),
            priority=priority,
            content=f"{candidate_label}:\n{candidate_json}",
            provenance={"evaluation_pass_id": evaluation_pass_id},
        ),
    ]


def assemble_semantic_qa_context(
    *,
    manifest_id: str,
    evaluation_pass_id: str,
    evaluation_target_role: str,
    inference_id: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    role_contributions: list[PromptContribution],
    authority_references: list[dict[str, Any]],
    candidate_package: dict[str, Any],
    candidate_label: str = "Candidate under evaluation",
    character_id: str | None = None,
    include_default_transport: bool = True,
) -> tuple[list[PromptContribution], list[str]]:
    """Assemble role-neutral semantic-QA manifest contributions."""
    normalized_refs, ref_errors = validate_authority_references(authority_references)
    contributions = list(role_contributions)
    if include_default_transport:
        contributions = append_authority_references_contribution(
            contributions,
            manifest_id=manifest_id,
            authority_references=normalized_refs,
            evaluation_pass_id=evaluation_pass_id,
        )
        contributions = append_candidate_package_contribution(
            contributions,
            manifest_id=manifest_id,
            candidate_package=candidate_package,
            evaluation_pass_id=evaluation_pass_id,
            candidate_label=candidate_label,
        )
    return contributions, ref_errors


def build_semantic_qa_context_response(
    *,
    manifest_id: str,
    evaluation_pass_id: str,
    evaluation_target_role: str,
    inference_id: str,
    inference_kind: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    role_contributions: list[PromptContribution],
    authority_references: list[dict[str, Any]],
    candidate_package: dict[str, Any],
    candidate_label: str = "Candidate under evaluation",
    character_id: str | None = None,
    include_default_transport: bool = True,
) -> SemanticQaContextPrepareResponse:
    contributions, _ref_errors = assemble_semantic_qa_context(
        manifest_id=manifest_id,
        evaluation_pass_id=evaluation_pass_id,
        evaluation_target_role=evaluation_target_role,
        inference_id=inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        role_contributions=role_contributions,
        authority_references=authority_references,
        candidate_package=candidate_package,
        candidate_label=candidate_label,
        character_id=character_id,
        include_default_transport=include_default_transport,
    )
    from .manifest_validation import validate_contribution_package

    validate_contribution_package(inference_kind, contributions)
    normalized_refs, _ = validate_authority_references(authority_references)
    return SemanticQaContextPrepareResponse(
        manifest_id=manifest_id,
        evaluation_pass_id=evaluation_pass_id,
        evaluation_target_role=evaluation_target_role,
        inference_id=inference_id,
        inference_kind=inference_kind,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        character_id=character_id,
        contributions=tuple(contributions),
        authority_references=tuple(normalized_refs),
        candidate_package=dict(candidate_package),
    )
