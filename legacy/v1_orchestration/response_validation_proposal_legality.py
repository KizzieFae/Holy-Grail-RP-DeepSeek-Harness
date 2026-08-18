"""Pre-commit proposal legality — continuity vs SceneState (GitHub #232)."""

from __future__ import annotations

PROPOSAL_LEGALITY_TAG = "[PROPOSAL_LEGALITY]"


def is_proposal_legality_rejection_reason(rejection_reason: str) -> bool:
    return str(rejection_reason or "").startswith(PROPOSAL_LEGALITY_TAG)


def format_proposal_legality_rejection(
    *,
    reason_code: str,
    reason_detail: str,
) -> str:
    code = str(reason_code or "").strip()
    detail = str(reason_detail or "").strip()
    msg = f"{PROPOSAL_LEGALITY_TAG} Proposal batch illegal vs committed scene state."
    if code:
        msg += f" Reason code: {code}."
    if detail:
        msg += f" {detail}"
    return msg


def format_proposal_legality_retry_note(
    *,
    rejection_reason: str,
    reason_code: str = "",
) -> str:
    code = str(reason_code or "").strip()
    detail = str(rejection_reason or "").strip()
    lines = [
        "IMPORTANT: Your previous move was rejected for proposal legality.",
        "Your typed semantic_proposals are illegal given current scene state "
        "(must_remain, on-stage/off-stage, excursion state).",
        "Revise or omit proposals — beats alone do not commit covered semantics.",
        "Do not rely on prose, tags, or heuristic exit/tag paths to commit presence.",
    ]
    if code:
        lines.append(f"Reason code: {code}.")
    if detail:
        lines.append(f"Detail: {detail}")
    return "\n".join(lines)
