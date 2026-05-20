"""Canonical audit decision record for semantic proposal authority (GitHub #233).

Observational contract only — projects runtime ``ProposalAuthorityContext`` and
pre-commit assessments; does not evaluate legality or mutate continuity.
"""

from __future__ import annotations

from typing import Any

from continuity_semantic_proposals import (
    PROPOSAL_OUTCOME_ACCEPT,
    ProposalAuthorityContext,
    ProposalAuthorityOutcome,
)

SCHEMA_VERSION = "1"

ACCEPTED_PROPOSAL_BATCH_NOTE = (
    "Read-only copy of typed proposals authorized for covered compile on this "
    "attempt. Not SceneState. Not mutation proof. Not continuity commit evidence."
)

COMMIT_PROOF_SCENE_STATE_FIELD = "context_snapshot.scene_state_after"


def semantic_proposals_on_move(move: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(move, dict):
        return []
    raw = move.get("semantic_proposals")
    if not isinstance(raw, list) or not raw:
        return []
    return [item for item in raw if isinstance(item, dict)]


def should_emit_semantic_proposal_decision(
    move: dict[str, Any] | None,
    *,
    proposal_authority_context: ProposalAuthorityContext | None = None,
    proposal_coherence_assessment: dict[str, Any] | None = None,
    legality_evaluated: bool = False,
    force_success_character_row: bool = False,
) -> bool:
    if force_success_character_row:
        return True
    if legality_evaluated or proposal_authority_context is not None:
        return True
    if proposal_coherence_assessment is not None:
        return True
    return bool(semantic_proposals_on_move(move))


def _coherence_status_from_assessment(
    assessment: dict[str, Any] | None,
    *,
    proposals_present: bool,
) -> str:
    if not proposals_present:
        return "absent"
    if not isinstance(assessment, dict):
        return "skipped"
    if assessment.get("status") == "rejected_structural":
        return "contradicted"
    status = str(assessment.get("status", "") or "").strip()
    if status == "contradicted":
        return "contradicted"
    if status == "aligned":
        return "aligned"
    return "skipped"


def _emitted_items(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, item in enumerate(proposals):
        row: dict[str, Any] = {"index": index}
        for key in ("kind", "character", "operation"):
            if key in item:
                row[key] = item[key]
        items.append(row)
    return items


def build_semantic_proposal_decision(
    *,
    move: dict[str, Any] | None,
    proposal_authority_context: ProposalAuthorityContext | None,
    lifecycle_phase: str,
    attempt_index: int,
    terminal: bool,
    retry_class: str | None,
    proposal_coherence_assessment: dict[str, Any] | None = None,
    legality_evaluated: bool = False,
    continuity_turn_index: int | None = None,
    include_commit_proof_pointer: bool = False,
    process_turn_ran: bool | None = None,
) -> dict[str, Any]:
    proposals = semantic_proposals_on_move(move)
    proposals_present = bool(proposals)

    batch: dict[str, Any] = {
        "accepted_count": 0,
        "process_turn_authorized": False,
        "covered_compile_authorized": False,
    }

    if legality_evaluated and proposal_authority_context is not None:
        outcome = proposal_authority_context.outcome.value
        batch["authority_outcome"] = outcome
        batch["reason_code"] = str(proposal_authority_context.reason_code or "")
        batch["reason_detail"] = str(proposal_authority_context.reason_detail or "")
        if outcome == PROPOSAL_OUTCOME_ACCEPT:
            accepted = list(proposal_authority_context.accepted_proposals)
            batch["accepted_count"] = len(accepted)
            batch["covered_compile_authorized"] = True
        elif proposal_authority_context.outcome == ProposalAuthorityOutcome.NO_PROPOSAL:
            batch["accepted_count"] = 0
        else:
            batch["accepted_count"] = 0

    if process_turn_ran is not None:
        batch["process_turn_authorized"] = bool(process_turn_ran)
    elif lifecycle_phase in ("committed_attempt", "committed_attempt_rolled_back"):
        batch["process_turn_authorized"] = True
        if (
            proposal_authority_context is not None
            and proposal_authority_context.outcome == ProposalAuthorityOutcome.ACCEPT
        ):
            batch["covered_compile_authorized"] = True

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "lifecycle_phase": lifecycle_phase,
        "batch": batch,
        "pre_commit": {
            "coherence_status": _coherence_status_from_assessment(
                proposal_coherence_assessment,
                proposals_present=proposals_present,
            ),
            "legality_evaluated": bool(legality_evaluated),
        },
        "attempt": {
            "attempt_index": int(attempt_index),
            "terminal": bool(terminal),
            "retry_class": retry_class,
        },
        "emitted": {
            "present": proposals_present,
            "count": len(proposals),
            "items": _emitted_items(proposals),
        },
        "doctrine": {
            "legacy_covered_commit_paths_removed": True,
        },
    }

    if (
        legality_evaluated
        and proposal_authority_context is not None
        and proposal_authority_context.outcome == ProposalAuthorityOutcome.ACCEPT
    ):
        record["accepted_proposal_batch"] = [
            dict(item) for item in proposal_authority_context.accepted_proposals
        ]
        record["accepted_proposal_batch_note"] = ACCEPTED_PROPOSAL_BATCH_NOTE

    if include_commit_proof_pointer and continuity_turn_index is not None:
        record["commit_proof_pointer"] = {
            "continuity_turn_index": int(continuity_turn_index),
            "scene_state_field": COMMIT_PROOF_SCENE_STATE_FIELD,
        }

    return record
