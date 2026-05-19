"""Pre-commit proposal coherence — structural checks (GitHub #231).

Deterministic self-only and proposal-set consistency only. No prose regex.
Beats↔proposal contradiction uses ``semantic_validation.assess_proposal_beat_contradiction``.
"""

from __future__ import annotations

from typing import Any

from character_move_adapters import move_schema_version

PROPOSAL_SCOPE_TAG = "[PROPOSAL_SCOPE]"
PROPOSAL_INCONSISTENT_TAG = "[PROPOSAL_INCONSISTENT]"
PROPOSAL_COHERENCE_TAG = "[PROPOSAL_COHERENCE]"

REASON_SCOPE_NON_SELF = "scope_non_self"
REASON_PROPOSAL_SET_CONFLICT = "proposal_set_conflict"

_VALID_REASON_CODES = frozenset(
    {
        REASON_SCOPE_NON_SELF,
        REASON_PROPOSAL_SET_CONFLICT,
        "off_focal_vs_beats",
        "reentry_vs_beats",
        "excursion_open_vs_beats",
        "excursion_close_vs_beats",
        "checker_parse_error",
        "checker_disabled",
    }
)


def is_proposal_rejection_reason(rejection_reason: str) -> bool:
    r = str(rejection_reason or "")
    return r.startswith(PROPOSAL_SCOPE_TAG) or r.startswith(
        PROPOSAL_INCONSISTENT_TAG
    ) or r.startswith(PROPOSAL_COHERENCE_TAG)


def _semantic_proposals_list(move: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(move, dict):
        return []
    raw = move.get("semantic_proposals")
    if not isinstance(raw, list) or not raw:
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(item)
    return out


def validate_proposal_structural_coherence(
    move: dict[str, Any] | None,
    *,
    acting_character: str,
) -> tuple[bool, str, str]:
    """Return ``(is_valid, rejection_reason, reason_code)``.

    ``reason_code`` is empty when valid.
    """
    if move_schema_version(move) != 2:
        return True, "", ""

    proposals = _semantic_proposals_list(move)
    if not proposals:
        return True, "", ""

    actor = str(acting_character or "").strip()
    if not actor:
        return True, "", ""

    scoped: list[dict[str, Any]] = []
    for i, item in enumerate(proposals):
        subj = str(item.get("character", "") or "").strip()
        if subj != actor:
            return (
                False,
                (
                    f"{PROPOSAL_SCOPE_TAG} semantic_proposals[{i}].character "
                    f"must be the acting character ({actor!r}); got {subj!r}."
                ),
                REASON_SCOPE_NON_SELF,
            )
        scoped.append(item)

    kinds: list[str] = []
    ops: list[str | None] = []
    for item in scoped:
        kinds.append(str(item.get("kind", "") or "").strip())
        op = item.get("operation", None)
        ops.append(str(op).strip().lower() if isinstance(op, str) else None)

    kind_set = set(kinds)
    if "off_focal" in kind_set and "reentry" in kind_set:
        return (
            False,
            (
                f"{PROPOSAL_INCONSISTENT_TAG} Cannot declare both off_focal and "
                f"reentry for {actor!r} in the same move."
            ),
            REASON_PROPOSAL_SET_CONFLICT,
        )

    if kinds.count("off_focal") > 1 or kinds.count("reentry") > 1:
        return (
            False,
            (
                f"{PROPOSAL_INCONSISTENT_TAG} Duplicate proposal kind for {actor!r} "
                f"in the same move."
            ),
            REASON_PROPOSAL_SET_CONFLICT,
        )

    exc_indices = [i for i, k in enumerate(kinds) if k == "excursion_lifecycle"]
    if len(exc_indices) >= 2:
        exc_ops = [ops[i] for i in exc_indices]
        if "open" in exc_ops and "close" in exc_ops:
            return (
                False,
                (
                    f"{PROPOSAL_INCONSISTENT_TAG} Cannot declare excursion_lifecycle "
                    f"open and close for {actor!r} in the same move."
                ),
                REASON_PROPOSAL_SET_CONFLICT,
            )

    if len(exc_indices) > 1:
        dup_op = [o for o in exc_ops if o]
        if len(dup_op) != len(set(dup_op)):
            return (
                False,
                (
                    f"{PROPOSAL_INCONSISTENT_TAG} Duplicate excursion_lifecycle "
                    f"operation for {actor!r} in the same move."
                ),
                REASON_PROPOSAL_SET_CONFLICT,
            )

    return True, "", ""


def format_proposal_coherence_retry_note(
    *,
    rejection_reason: str,
    reason_code: str = "",
) -> str:
    code = str(reason_code or "").strip()
    detail = str(rejection_reason or "").strip()
    lines = [
        "IMPORTANT: Your previous move was rejected for proposal coherence.",
        "Align beats[] with your typed semantic_proposals (or omit semantic_proposals "
        "when you have no presence/off-focal commit intent to declare).",
        "Proposals are semantic commit intent only — not a substitute for beats.",
    ]
    if code:
        lines.append(f"Reason code: {code}.")
    if detail:
        lines.append(f"Detail: {detail}")
    return "\n".join(lines)
