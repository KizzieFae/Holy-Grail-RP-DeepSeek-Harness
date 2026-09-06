"""Director-owned semantic-QA context preparation (#26)."""

from __future__ import annotations

from typing import Any

from domain.modules.authority_reference import validate_authority_references

from .context_substrate import auth_projections_to_contributions

from .contract import (
    DirectorSemanticQaContextPrepareRequest,
    PromptContribution,
    SemanticQaContextPrepareResponse,
)
from .director_context_digests import (
    build_director_scene_evidence_contributions,
    director_scene_condition_flags,
    validate_director_context_completeness,
)
from .semantic_qa_context import (
    assemble_semantic_qa_context,
    build_semantic_qa_context_response,
)
from .session_state import LiveSession, RoundFixture

DIRECTOR_SEMANTIC_QA_RUBRIC = (
    "Evaluate the Director decision candidate for defensibility against bounded scene evidence. "
    "Judge only these five dimensions:\n"
    "- dir_actor_suitability: eligible-actor fit, explicit user addressee, spotlight balance. "
    "Hard findings may cite authoritative user:* and orch:* refs only.\n"
    "- dir_scene_contradiction: contradiction with committed scene facts. "
    "Hard findings require authoritative refs.\n"
    "- dir_env_event: non-empty environment_event redundancy or implausibility. "
    "Hard allowed for near-duplicate committed environment evidence.\n"
    "- dir_pacing_tension: tension_shift vs scene phase/pressures. Soft by default; "
    "advisory issue:*:required_next_step refs cannot support hard findings.\n"
    "- dir_reason_coherence: reason explains chosen actor/tension/env. Soft only.\n"
    "Do not judge missing context, global creative optimality, or replacement actor choice. "
    "Output only JSON matching schema hg_semantic_qa_result_v1. "
    "Hard findings require valid authoritative ref_id citations from the references block. "
    "Do not emit replacement Director JSON or bind next_actor."
)


def _evaluator_instruction_contribution(
    *,
    manifest_id: str,
    evaluation_pass_id: str,
) -> PromptContribution:
    return PromptContribution(
        contribution_id=f"{manifest_id}-director-semantic-qa-instruction",
        source_kind="inference_instruction",
        authority_class="derived",
        knowledge_ids=(f"semantic_qa:director:{evaluation_pass_id}",),
        priority=30,
        content=DIRECTOR_SEMANTIC_QA_RUBRIC,
        provenance={"evaluation_pass_id": evaluation_pass_id},
    )


def prepare_director_semantic_qa_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    req: DirectorSemanticQaContextPrepareRequest,
    *,
    available: list[str],
    auth_projections: list[Any],
    participation_mode: str | None = None,
) -> tuple[list[PromptContribution], list[dict[str, Any]], dict[str, Any]]:
    """Build Director scene evidence contributions shared with prepare_director_context."""
    manifest_id = f"manifest-director-semantic-qa-{req.evaluation_pass_id}"
    auth_contributions = auth_projections_to_contributions(manifest_id, auth_projections)
    scene_contributions, authority_refs = build_director_scene_evidence_contributions(
        fixture,
        rnd,
        manifest_id,
        available,
        participation_mode=participation_mode,
        auth_contributions=auth_contributions,
    )
    flags = director_scene_condition_flags(fixture, rnd, available)
    role_contributions = [
        *scene_contributions,
        _evaluator_instruction_contribution(
            manifest_id=manifest_id,
            evaluation_pass_id=req.evaluation_pass_id,
        ),
    ]
    validate_director_context_completeness(
        role_contributions,
        has_round_turns=flags["has_round_turns"],
        multiple_eligible=flags["multiple_eligible"],
        has_active_issues=flags["has_active_issues"],
        has_user_turn=flags["has_user_turn"],
    )
    candidate_package = {
        "candidate_decision": dict(req.candidate_decision),
        "raw_model_output": req.raw_model_output,
    }
    return role_contributions, authority_refs, candidate_package


def build_director_semantic_qa_context_response(
    *,
    manifest_id: str,
    evaluation_pass_id: str,
    inference_id: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    role_contributions: list[PromptContribution],
    authority_references: list[dict[str, Any]],
    candidate_package: dict[str, Any],
) -> SemanticQaContextPrepareResponse:
    """Assemble Director semantic-QA response; fail closed on invalid authority refs."""
    normalized_refs, ref_errors = validate_authority_references(authority_references)
    if ref_errors:
        raise ValueError(
            "Director semantic QA context preparation failed: "
            + "; ".join(ref_errors)
        )

    _, assemble_errors = assemble_semantic_qa_context(
        manifest_id=manifest_id,
        evaluation_pass_id=evaluation_pass_id,
        evaluation_target_role="director",
        inference_id=inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        role_contributions=role_contributions,
        authority_references=normalized_refs,
        candidate_package=candidate_package,
        candidate_label="Director decision candidate",
        character_id=None,
        include_default_transport=True,
    )
    if assemble_errors:
        raise ValueError(
            "Director semantic QA context assembly failed: "
            + "; ".join(assemble_errors)
        )

    return build_semantic_qa_context_response(
        manifest_id=manifest_id,
        evaluation_pass_id=evaluation_pass_id,
        evaluation_target_role="director",
        inference_id=inference_id,
        inference_kind="director_semantic_qa",
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        role_contributions=role_contributions,
        authority_references=normalized_refs,
        candidate_package=candidate_package,
        candidate_label="Director decision candidate",
        character_id=None,
        include_default_transport=True,
    )
