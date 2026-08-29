"""Bounded Character epistemic context for Layer B projection evaluation (#63)."""

from __future__ import annotations

from typing import Any

from .character_epistemic import compute_known_by_snapshot_id, resolve_basis_exposure
from .continuity_context_projector import project_authoritative_context
from .plot_cognition_orchestration_contract import (
    CHARACTER_EPISTEMIC_CONTEXT_SCHEMA,
    CharacterEpistemicContextEnvelope,
    StorytellerOrchestrationPolicy,
    compute_visibility_digest,
)
from .plot_cognition_projection_contract import CharacterAdvisoryCandidate
from .semantic_evaluation_context import build_authority_references
from .session_state import LiveSession

EPISTEMIC_PROHIBITION_BLOCK = (
    "Evaluate only whether the proposed Character-facing advisory text communicates or "
    "materially implies information outside the Character's permitted epistemic envelope. "
    "Do not treat scope/relevance markers as proof of knowledge. "
    "Do not authorize exposure of withheld basis, other Characters' private knowledge, "
    "or global plot cognition."
)


def _character_known_event_summaries(
    fixture: LiveSession,
    character_id: str,
    *,
    max_items: int,
    max_chars_each: int,
) -> list[str]:
    summaries: list[str] = []
    for event in getattr(fixture.manager, "public_events", []) or []:
        known_by = {str(item) for item in (getattr(event, "known_by", []) or [])}
        if character_id not in known_by:
            continue
        text = str(
            getattr(event, "summary", "")
            or getattr(event, "description", "")
            or getattr(event, "content", "")
            or ""
        ).strip()
        if not text:
            text = str(getattr(event, "event_id", "") or "")
        if not text:
            continue
        summaries.append(f"Known event: {text[:max_chars_each]}")
        if len(summaries) >= max_items:
            break
    return summaries


def _exposable_basis_summaries(
    fixture: LiveSession,
    *,
    character_id: str,
    candidate: CharacterAdvisoryCandidate,
    max_items: int,
) -> tuple[list[str], list[dict[str, str]]]:
    exposure = resolve_basis_exposure(
        fixture,
        character_id=character_id,
        basis_refs=candidate.basis_refs,
    )
    exposable: list[str] = []
    withheld_index: list[dict[str, str]] = []
    for facet_id in exposure.exposable_facet_ids[:max_items]:
        exposable.append(f"Exposable basis facet: {facet_id}")
    for facet_id in exposure.withheld_facet_ids:
        category = facet_id.split(":", 1)[0] if ":" in facet_id else "unknown"
        withheld_index.append(
            {
                "facet_id": facet_id,
                "category": category,
                "reason": "withheld_from_character",
            }
        )
    return exposable, withheld_index


def _scene_visible_facts(
    fixture: LiveSession,
    *,
    character_id: str,
    hg_round_id: str,
    turn_index: int,
    max_items: int,
) -> list[str]:
    facts: list[str] = []
    projections = project_authoritative_context(
        fixture,
        role="character",
        character_id=character_id,
        hg_scene_id=fixture.hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
    )
    for projection in projections[:max_items]:
        text = str(getattr(projection, "content", "") or "").strip()
        if text:
            facts.append(f"Scene-visible: {text[:500]}")
    return facts


def build_character_epistemic_context_envelope(
    fixture: LiveSession,
    *,
    character_id: str,
    candidate: CharacterAdvisoryCandidate,
    hg_round_id: str,
    turn_index: int,
    authority_fingerprint: str | None,
    overlay_revision: int | None,
    policy: StorytellerOrchestrationPolicy | None = None,
) -> CharacterEpistemicContextEnvelope:
    """Build bounded semantic epistemic material for Layer B evaluation."""
    orch_policy = policy or StorytellerOrchestrationPolicy(
        schema="hg_plot_cognition_orchestration_policy_v1"
    )
    known_by_snapshot_id = compute_known_by_snapshot_id(fixture, character_id)
    known_events = _character_known_event_summaries(
        fixture,
        character_id,
        max_items=orch_policy.max_semantic_context_items // 4,
        max_chars_each=400,
    )
    exposable_basis, withheld_index = _exposable_basis_summaries(
        fixture,
        character_id=character_id,
        candidate=candidate,
        max_items=orch_policy.max_semantic_context_items // 4,
    )
    scene_facts = _scene_visible_facts(
        fixture,
        character_id=character_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        max_items=orch_policy.max_semantic_context_items // 4,
    )
    authority_refs = build_authority_references(
        fixture,
        character_id=character_id,
        hg_round_id=hg_round_id,
    )
    authority_summaries = [
        f"Authority ref {ref.get('ref_id')}: {str(ref.get('text', ''))[:300]}"
        for ref in authority_refs[:4]
    ]
    semantic_material = tuple(
        (
            EPISTEMIC_PROHIBITION_BLOCK,
            f"Proposed candidate text: {candidate.text.strip()}",
            *known_events,
            *exposable_basis,
            *scene_facts,
            *authority_summaries,
        )[: orch_policy.max_semantic_context_items]
    )
    total_chars = sum(len(item) for item in semantic_material)
    if total_chars > orch_policy.max_semantic_context_chars:
        trimmed: list[str] = []
        running = 0
        for item in semantic_material:
            if running + len(item) > orch_policy.max_semantic_context_chars:
                break
            trimmed.append(item)
            running += len(item)
        semantic_material = tuple(trimmed)

    return CharacterEpistemicContextEnvelope(
        schema=CHARACTER_EPISTEMIC_CONTEXT_SCHEMA,
        character_id=character_id,
        known_by_snapshot_id=known_by_snapshot_id,
        authority_fingerprint=authority_fingerprint,
        overlay_revision=overlay_revision,
        visibility_digest=compute_visibility_digest(semantic_material),
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        candidate_id=candidate.candidate_id,
        source_kind=candidate.source_kind,
        lineage=candidate.lineage,
        semantic_material=semantic_material,
        withheld_basis_index=tuple(withheld_index),
        identity_evidence={
            "candidate_id": candidate.candidate_id,
            "source_kind": candidate.source_kind,
            "lineage": list(candidate.lineage),
        },
    )


def envelope_to_evaluator_contributions(
    envelope: CharacterEpistemicContextEnvelope,
    *,
    manifest_id: str,
) -> list[dict[str, Any]]:
    """Serialize envelope into manifest contribution payloads for DSH inference."""
    contributions: list[dict[str, Any]] = []
    for index, material in enumerate(envelope.semantic_material):
        contributions.append(
            {
                "contribution_id": f"{manifest_id}-epistemic-{index}",
                "source_kind": "active_constraints" if index == 0 else "derived",
                "authority_class": "derived",
                "knowledge_ids": [f"epistemic:{envelope.candidate_id}:{index}"],
                "priority": 20 + index,
                "content": material,
                "provenance": {
                    "candidate_id": envelope.candidate_id,
                    "known_by_snapshot_id": envelope.known_by_snapshot_id,
                },
            }
        )
    if envelope.withheld_basis_index:
        withheld_lines = [
            f"WITHHELD {item['facet_id']} ({item['category']}): {item['reason']}"
            for item in envelope.withheld_basis_index
        ]
        contributions.append(
            {
                "contribution_id": f"{manifest_id}-withheld-index",
                "source_kind": "active_constraints",
                "authority_class": "derived",
                "knowledge_ids": [f"withheld:{envelope.candidate_id}"],
                "priority": 19,
                "content": "Withheld basis index (categories only):\n" + "\n".join(withheld_lines),
                "provenance": {"candidate_id": envelope.candidate_id},
            }
        )
    return contributions
