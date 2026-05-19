"""Continuity authority for character ``semantic_proposals`` (GitHub #232).

Accepted proposals are the sole commit source for v1 covered semantics.
Reconstruction-era paths are suppressed elsewhere — not merged here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from continuity_mutation_pipeline_types import (
    CanonicalAtom,
    ContinuityMutationType,
    MutationRequest,
    MutationSourceClass,
)
from continuity_presence_helpers import (
    PresenceAuthorityScratch,
    apply_canonical_reentry_scratch,
)

class ContinuityProposalLegalityError(ValueError):
    """Proposal batch illegal vs committed scene state (#232)."""


PROPOSAL_OUTCOME_ACCEPT = "accept"
PROPOSAL_OUTCOME_REJECT = "reject"
PROPOSAL_OUTCOME_NO_PROPOSAL = "no_proposal"

REASON_MUST_REMAIN_OFF_FOCAL = "must_remain_off_focal"
REASON_ILLEGAL_ALREADY_OFF_FOCAL = "illegal_already_off_focal"
REASON_ILLEGAL_ALREADY_ONSTAGE = "illegal_already_onstage"
REASON_ILLEGAL_REENTRY_ON_EXCURSION = "illegal_reentry_on_excursion"
REASON_ILLEGAL_EXCURSION_OPEN_ACTIVE = "illegal_excursion_open_active"
REASON_ILLEGAL_EXCURSION_NO_ACTIVE = "illegal_excursion_no_active"
REASON_SCOPE_NON_SELF = "scope_non_self"
REASON_UNKNOWN_KIND = "unknown_proposal_kind"
REASON_MISSING_OPERATION = "missing_excursion_operation"


class ProposalAuthorityOutcome(str, Enum):
    ACCEPT = PROPOSAL_OUTCOME_ACCEPT
    REJECT = PROPOSAL_OUTCOME_REJECT
    NO_PROPOSAL = PROPOSAL_OUTCOME_NO_PROPOSAL


@dataclass(frozen=True)
class ProposalAuthorityContext:
    outcome: ProposalAuthorityOutcome
    accepted_proposals: tuple[dict[str, Any], ...] = ()
    reason_code: str = ""
    reason_detail: str = ""


def _semantic_proposals_list(move: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(move, dict):
        return []
    raw = move.get("semantic_proposals")
    if not isinstance(raw, list) or not raw:
        return []
    return [item for item in raw if isinstance(item, dict)]


def _active_excursion_id_for_character(
    excursions: dict[str, Any], character: str
) -> str | None:
    actor = str(character or "").strip()
    if not actor:
        return None
    for eid, rec in excursions.items():
        if rec is None:
            continue
        status = getattr(rec, "status", None)
        status_val = getattr(status, "value", status)
        if str(status_val or "").lower() != "active":
            continue
        participants = getattr(rec, "participant_character_ids", None) or []
        if actor in {str(p).strip() for p in participants if str(p).strip()}:
            return str(eid).strip()
    return None


def _character_on_active_excursion(
    active_excursion_character_ids: set[str], character: str
) -> bool:
    return str(character or "").strip() in active_excursion_character_ids


def evaluate_proposal_legality(
    move: dict[str, Any],
    *,
    acting_character: str,
    scene_state: dict[str, Any],
    active_excursion_character_ids: set[str] | None = None,
    excursions: dict[str, Any] | None = None,
) -> ProposalAuthorityContext:
    """Pure legality evaluation — no ``SceneState`` mutation."""
    proposals = _semantic_proposals_list(move)
    if not proposals:
        return ProposalAuthorityContext(outcome=ProposalAuthorityOutcome.NO_PROPOSAL)

    actor = str(acting_character or "").strip()
    present = {
        str(x).strip()
        for x in (scene_state.get("present_characters") or [])
        if str(x).strip()
    }
    constraints = scene_state.get("character_presence_constraints") or {}
    if not isinstance(constraints, dict):
        constraints = {}
    e_active = set(active_excursion_character_ids or ())
    exc_map = excursions if isinstance(excursions, dict) else {}

    for i, item in enumerate(proposals):
        subj = str(item.get("character", "") or "").strip()
        if subj != actor:
            return ProposalAuthorityContext(
                outcome=ProposalAuthorityOutcome.REJECT,
                reason_code=REASON_SCOPE_NON_SELF,
                reason_detail=(
                    f"semantic_proposals[{i}].character must be acting character "
                    f"{actor!r}; got {subj!r}."
                ),
            )

        kind = str(item.get("kind", "") or "").strip()
        if kind == "off_focal":
            if str(constraints.get(actor, "") or "") == "must_remain":
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_MUST_REMAIN_OFF_FOCAL,
                    reason_detail=(
                        f"off_focal proposal illegal under must_remain for {actor!r}."
                    ),
                )
            if actor not in present:
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_ILLEGAL_ALREADY_OFF_FOCAL,
                    reason_detail=f"off_focal illegal: {actor!r} is not on-stage.",
                )
            if _character_on_active_excursion(e_active, actor):
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_ILLEGAL_ALREADY_OFF_FOCAL,
                    reason_detail=(
                        f"off_focal illegal: {actor!r} is on an active excursion."
                    ),
                )
        elif kind == "reentry":
            if actor in present:
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_ILLEGAL_ALREADY_ONSTAGE,
                    reason_detail=f"reentry illegal: {actor!r} is already on-stage.",
                )
            if _character_on_active_excursion(e_active, actor):
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_ILLEGAL_REENTRY_ON_EXCURSION,
                    reason_detail=(
                        f"reentry illegal: {actor!r} is on an active excursion."
                    ),
                )
        elif kind == "excursion_lifecycle":
            op_raw = item.get("operation")
            if not isinstance(op_raw, str) or not str(op_raw).strip():
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_MISSING_OPERATION,
                    reason_detail=(
                        "excursion_lifecycle requires operation open|update|close."
                    ),
                )
            op = str(op_raw).strip().lower()
            active_eid = _active_excursion_id_for_character(exc_map, actor)
            if op == "open":
                if active_eid is not None:
                    return ProposalAuthorityContext(
                        outcome=ProposalAuthorityOutcome.REJECT,
                        reason_code=REASON_ILLEGAL_EXCURSION_OPEN_ACTIVE,
                        reason_detail=(
                            f"excursion open illegal: {actor!r} already on active "
                            f"excursion {active_eid!r}."
                        ),
                    )
            elif op in ("update", "close"):
                if active_eid is None:
                    return ProposalAuthorityContext(
                        outcome=ProposalAuthorityOutcome.REJECT,
                        reason_code=REASON_ILLEGAL_EXCURSION_NO_ACTIVE,
                        reason_detail=(
                            f"excursion {op} illegal: no active excursion for {actor!r}."
                        ),
                    )
            else:
                return ProposalAuthorityContext(
                    outcome=ProposalAuthorityOutcome.REJECT,
                    reason_code=REASON_UNKNOWN_KIND,
                    reason_detail=f"unknown excursion_lifecycle operation {op!r}.",
                )
        else:
            return ProposalAuthorityContext(
                outcome=ProposalAuthorityOutcome.REJECT,
                reason_code=REASON_UNKNOWN_KIND,
                reason_detail=f"unknown proposal kind {kind!r}.",
            )

    return ProposalAuthorityContext(
        outcome=ProposalAuthorityOutcome.ACCEPT,
        accepted_proposals=tuple(proposals),
    )


def compile_proposal_excursion_mutations(
    accepted_proposals: tuple[dict[str, Any], ...],
    *,
    acting_character: str,
    excursions: dict[str, Any],
) -> list[MutationRequest]:
    """Compile accepted excursion_lifecycle proposals to mutation requests."""
    actor = str(acting_character or "").strip()
    out: list[MutationRequest] = []
    for item in accepted_proposals:
        if str(item.get("kind", "") or "").strip() != "excursion_lifecycle":
            continue
        op = str(item.get("operation", "") or "").strip().lower()
        if op == "open":
            out.append(
                MutationRequest(
                    mutation_type=ContinuityMutationType.EXCURSION_OPEN,
                    atom=CanonicalAtom.EXCURSION_LIFECYCLE,
                    source=MutationSourceClass.M,
                    payload={
                        "operation": "open",
                        "participant_character_ids": [actor],
                        "proposal_sourced": True,
                    },
                )
            )
        elif op == "update":
            eid = _active_excursion_id_for_character(excursions, actor)
            if not eid:
                continue
            out.append(
                MutationRequest(
                    mutation_type=ContinuityMutationType.EXCURSION_UPDATE,
                    atom=CanonicalAtom.EXCURSION_LIFECYCLE,
                    source=MutationSourceClass.M,
                    payload={
                        "operation": "update",
                        "excursion_id": eid,
                        "participant_character_ids": [actor],
                        "proposal_sourced": True,
                    },
                )
            )
        elif op == "close":
            eid = _active_excursion_id_for_character(excursions, actor)
            if not eid:
                continue
            out.append(
                MutationRequest(
                    mutation_type=ContinuityMutationType.EXCURSION_CLOSE,
                    atom=CanonicalAtom.EXCURSION_LIFECYCLE,
                    source=MutationSourceClass.M,
                    payload={
                        "operation": "close",
                        "excursion_id": eid,
                        "proposal_sourced": True,
                    },
                )
            )
    return out


def apply_accepted_proposal_presence_to_scratch(
    scratch: PresenceAuthorityScratch,
    accepted_proposals: tuple[dict[str, Any], ...],
    *,
    acting_character: str,
) -> None:
    """Apply off_focal / reentry covered semantics to presence scratch only."""
    actor = str(acting_character or "").strip()
    for item in accepted_proposals:
        kind = str(item.get("kind", "") or "").strip()
        subj = str(item.get("character", "") or "").strip()
        if subj != actor:
            continue
        if kind == "off_focal":
            scratch.present_characters = [
                n for n in scratch.present_characters if n != actor
            ]
            if actor not in scratch.offstage_characters:
                scratch.offstage_characters.append(actor)
            scratch.character_presence_status[actor] = "temporary_offstage"
        elif kind == "reentry":
            apply_canonical_reentry_scratch(scratch, actor)


def proposal_authority_metadata(ctx: ProposalAuthorityContext) -> dict[str, Any]:
    return {
        "proposal_authority_outcome": ctx.outcome.value,
        "proposal_authority_reason_code": ctx.reason_code,
        "proposal_authority_reason_detail": ctx.reason_detail,
        "proposal_authority_accepted_count": len(ctx.accepted_proposals),
    }
