"""Narrator-owned semantic-QA context preparation (#27)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_V2 = Path(__file__).resolve().parents[1]
if str(_V2) not in sys.path:
    sys.path.insert(0, str(_V2))
from domain.bootstrap import ensure_domain_paths  # noqa: E402

ensure_domain_paths()

from domain.modules.authority_reference import validate_authority_references  # noqa: E402
from perception_audibility_structured import redact_structured_move_for_orchestration  # noqa: E402

from .contract import (
    NarratorSemanticQaContextPrepareRequest,
    PromptContribution,
    SemanticQaContextPrepareResponse,
)
from .continuity_context_projector import project_authoritative_context
from .narrator_environment_packet import assemble_narrator_environment_packet
from .semantic_qa_context import (
    assemble_semantic_qa_context,
    build_semantic_qa_context_response,
)
from .session_state import LiveSession, RoundFixture

MAX_REF_CHARS = 1200

NARRATOR_SEMANTIC_QA_CORE_DIMENSIONS: tuple[str, ...] = (
    "nar_attribution_error",
    "nar_committed_contradiction",
    "nar_action_intention_distortion",
    "nar_psychological_invention",
    "nar_framing_distortion",
)

NARRATOR_SEMANTIC_QA_ENVIRONMENTAL_DIMENSIONS: tuple[str, ...] = (
    "nar_environmental_contradiction",
    "nar_environmental_under_description",
    "nar_environmental_repetition",
    "nar_environmental_invention",
)

NARRATOR_SEMANTIC_QA_DIMENSIONS: tuple[str, ...] = (
    *NARRATOR_SEMANTIC_QA_CORE_DIMENSIONS,
    *NARRATOR_SEMANTIC_QA_ENVIRONMENTAL_DIMENSIONS,
)

NARRATOR_SEMANTIC_QA_RUBRIC = (
    "Evaluate the Narrator presentation candidate for fidelity to bounded committed source "
    "evidence. This is presentation-fidelity review, not style optimization or continuity "
    "authority. Do not duplicate F1/F2 speech verbatim/order checks.\n"
    "Judge only these dimensions:\n"
    "- nar_attribution_error: material misassignment of speaker, actor, addressee, or "
    "ownership of an action/dialogue beat. Hard when contradicted by authoritative committed "
    "evidence. Not for preferred dialogue framing or POV style.\n"
    "- nar_committed_contradiction: material factual contradiction of committed move, "
    "authoritative scene state, or legitimate progression/canon/grounding evidence. Hard "
    "when supported by authoritative evidence. Do not reject richer but compatible description.\n"
    "- nar_action_intention_distortion: material alteration of what a character did, attempted, "
    "intended, pursued, refused, or risked relative to committed action/motivation evidence. "
    "Hard for substantive inversion or replacement.\n"
    "- nar_psychological_invention: material unsupported affirmative interior claims. Apply the "
    "closed-world rule: affirmative private knowledge, memory, belief, intention, desire, "
    "motivation, or emotional state requires support from legitimate committed source. Hard "
    "for material unsupported interior invention even without explicit contradiction. Do not "
    "ban inference, expressive prose, or faithful realization of committed motivation.\n"
    "- nar_framing_distortion: tone, metaphor, causal framing, or descriptive treatment that "
    "materially changes source meaning or character fidelity. Soft by default; hard only when "
    "authoritative evidence establishes clear material meaning inversion.\n"
    "- nar_environmental_contradiction: material contradiction or silent redesign of established "
    "environmental baseline / B2 properties from narrator_environment_baseline or cognition audit. "
    "Hard when supported by authoritative environmental refs.\n"
    "- nar_environmental_under_description: sterile summary or omission where environmental "
    "response was materially expected given triggering user action and cognition context. Soft.\n"
    "- nar_environmental_repetition: full redundant re-description of established environment "
    "without material turn need. Soft.\n"
    "- nar_environmental_invention: material unsupported environmental fact after "
    "ambiguity/forbidden/retrieval_failure/mediation_failure, or misuse of B1 to avoid B2. Hard.\n"
    "Authority rules:\n"
    "- Hard findings require valid authoritative_citation.ref_id from the authority references "
    "block with authority_class authoritative.\n"
    "- orch:* and other derived refs may support soft findings only, not hard rejection.\n"
    "- Accept faithful paraphrase, connective prose, sensory detail, metaphor, moderate emotional "
    "coloring, and harmless embellishment that does not establish consequential new facts.\n"
    "- Do not emit replacement Narrator prose or bind presentation authority.\n"
    "Output only JSON matching schema hg_semantic_qa_result_v1."
)


def _truncate(text: str, limit: int = MAX_REF_CHARS) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3] + "..."


def _authority_ref(
    *,
    ref_id: str,
    kind: str,
    authority_class: str,
    label: str,
    text: str,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ref_id": ref_id,
        "kind": kind,
        "authority_class": authority_class,
        "label": label,
        "text": text,
    }
    if provenance:
        payload["provenance"] = dict(provenance)
    return payload


def _refs_from_auth_projections(projections: list[Any]) -> list[dict[str, Any]]:
    """One citeable ref per projection knowledge id (deduped by ref_id)."""
    refs: list[dict[str, Any]] = []
    seen: set[str] = set()
    for proj in projections:
        content = _truncate(str(getattr(proj, "content", "") or ""))
        source_kind = str(getattr(proj, "source_kind", "") or "scene_reference")
        for kid in getattr(proj, "knowledge_ids", ()) or ():
            ref_id = str(kid or "").strip()
            if not ref_id or ref_id in seen:
                continue
            seen.add(ref_id)
            refs.append(
                _authority_ref(
                    ref_id=ref_id,
                    kind=source_kind,
                    authority_class=str(getattr(proj, "authority_class", "") or "authoritative"),
                    label=f"{source_kind} ({ref_id})",
                    text=content,
                    provenance=dict(getattr(proj, "provenance", {}) or {}),
                )
            )
    return refs


def build_narrator_authority_references(
    fixture: LiveSession,
    rnd: RoundFixture,
    *,
    turn_record: Any,
    auth_projections: list[Any],
) -> list[dict[str, Any]]:
    """Bounded citeable refs for semantic QA (single surface; no lane duplication)."""
    mgr = fixture.manager
    assert mgr.scene_state is not None
    present_labels = list(
        getattr(mgr.scene_state, "present_characters", None) or fixture.cast
    )
    commit_id = str(turn_record.domain_commit_id or "").strip()
    move = dict(turn_record.committed_move or {})
    narrate_move = redact_structured_move_for_orchestration(
        move,
        present_characters=present_labels,
    )
    refs: list[dict[str, Any]] = []

    if commit_id:
        refs.append(
            _authority_ref(
                ref_id=f"commit:{commit_id}",
                kind="committed_move",
                authority_class="authoritative",
                label=f"Committed move ({turn_record.character_id})",
                text=_truncate(json.dumps(narrate_move, ensure_ascii=False)),
                provenance={
                    "domain_commit_id": commit_id,
                    "character_id": turn_record.character_id,
                    "continuity_turn_index": turn_record.continuity_turn_index,
                },
            )
        )

    director_decision = dict(turn_record.director_decision or {})
    refs.append(
        _authority_ref(
            ref_id=f"orch:round:{rnd.hg_round_id}",
            kind="director_decision",
            authority_class="derived",
            label="Director decision (derived orchestration)",
            text=_truncate(json.dumps(director_decision, ensure_ascii=False)),
            provenance={
                "hg_round_id": rnd.hg_round_id,
                "visibility": "orchestration_projection",
            },
        )
    )

    refs.extend(_refs_from_auth_projections(auth_projections))

    try:
        env_packet, env_view = assemble_narrator_environment_packet(fixture)
        refs.append(
            _authority_ref(
                ref_id=f"env:{env_view.location_ref}",
                kind="narrator_environment_baseline",
                authority_class="authoritative",
                label="Narrator environmental baseline",
                text=_truncate(env_packet.render_summary()),
                provenance={"location_ref": env_view.location_ref},
            )
        )
    except (ValueError, AttributeError):
        pass

    merged: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for ref in refs:
        ref_id = str(ref.get("ref_id") or "").strip()
        if not ref_id or ref_id in seen_ids:
            continue
        seen_ids.add(ref_id)
        merged.append(ref)
    return merged


def build_narrator_semantic_qa_candidate_transport(
    *,
    candidate_presentation: str,
    domain_commit_id: str,
    character_id: str,
) -> dict[str, Any]:
    """QA transport payload: presentation under review plus correlation ids only."""
    return {
        "candidate_presentation": candidate_presentation,
        "domain_commit_id": domain_commit_id,
        "character_id": character_id,
    }


def prepare_narrator_semantic_qa_context(
    fixture: LiveSession,
    rnd: RoundFixture,
    req: NarratorSemanticQaContextPrepareRequest,
) -> tuple[list[PromptContribution], list[dict[str, Any]], dict[str, Any]]:
    turn_record = next(
        (turn for turn in rnd.character_turns if turn.domain_commit_id == req.domain_commit_id),
        None,
    )
    if turn_record is None:
        raise ValueError(
            f"narrator semantic QA requires committed move for domain_commit_id "
            f"{req.domain_commit_id}"
        )

    manifest_id = f"manifest-narrator-semantic-qa-{req.evaluation_pass_id}"
    auth_projections = project_authoritative_context(
        fixture,
        role="narrator",
        character_id=req.character_id,
        hg_scene_id=req.hg_scene_id,
        hg_round_id=req.hg_round_id,
        continuity_turn_index=turn_record.continuity_turn_index,
    )
    authority_refs = build_narrator_authority_references(
        fixture,
        rnd,
        turn_record=turn_record,
        auth_projections=auth_projections,
    )

    role_contributions: list[PromptContribution] = [
        PromptContribution(
            contribution_id=f"{manifest_id}-narrator-semantic-qa-instruction",
            source_kind="inference_instruction",
            authority_class="derived",
            knowledge_ids=(f"semantic_qa:narrator:{req.evaluation_pass_id}",),
            priority=30,
            content=NARRATOR_SEMANTIC_QA_RUBRIC,
            provenance={"evaluation_pass_id": req.evaluation_pass_id},
        ),
    ]

    candidate_package = {
        "candidate_presentation": req.candidate_presentation,
        "raw_model_output": req.raw_model_output,
        "domain_commit_id": req.domain_commit_id,
        "character_id": req.character_id,
    }
    return role_contributions, authority_refs, candidate_package


def build_narrator_semantic_qa_context_response(
    *,
    manifest_id: str,
    evaluation_pass_id: str,
    inference_id: str,
    hg_scene_id: str,
    hg_round_id: str,
    turn_index: int,
    character_id: str,
    role_contributions: list[PromptContribution],
    authority_references: list[dict[str, Any]],
    candidate_package: dict[str, Any],
) -> SemanticQaContextPrepareResponse:
    normalized_refs, ref_errors = validate_authority_references(authority_references)
    if ref_errors:
        raise ValueError(
            "Narrator semantic QA context preparation failed: "
            + "; ".join(ref_errors)
        )

    candidate_transport = build_narrator_semantic_qa_candidate_transport(
        candidate_presentation=str(candidate_package.get("candidate_presentation") or ""),
        domain_commit_id=str(candidate_package.get("domain_commit_id") or ""),
        character_id=str(candidate_package.get("character_id") or ""),
    )

    _, assemble_errors = assemble_semantic_qa_context(
        manifest_id=manifest_id,
        evaluation_pass_id=evaluation_pass_id,
        evaluation_target_role="narrator",
        inference_id=inference_id,
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        role_contributions=role_contributions,
        authority_references=normalized_refs,
        candidate_package=candidate_package,
        candidate_label="Narrator presentation candidate",
        character_id=character_id,
        include_default_transport=True,
        candidate_transport_package=candidate_transport,
    )
    if assemble_errors:
        raise ValueError(
            "Narrator semantic QA context assembly failed: "
            + "; ".join(assemble_errors)
        )

    return build_semantic_qa_context_response(
        manifest_id=manifest_id,
        evaluation_pass_id=evaluation_pass_id,
        evaluation_target_role="narrator",
        inference_id=inference_id,
        inference_kind="narrator_semantic_qa",
        hg_scene_id=hg_scene_id,
        hg_round_id=hg_round_id,
        turn_index=turn_index,
        role_contributions=role_contributions,
        authority_references=normalized_refs,
        candidate_package=candidate_package,
        candidate_label="Narrator presentation candidate",
        character_id=character_id,
        include_default_transport=True,
        candidate_transport_package=candidate_transport,
    )
