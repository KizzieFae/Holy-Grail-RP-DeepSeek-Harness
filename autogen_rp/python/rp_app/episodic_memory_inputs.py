"""Extract continuity sequences for episodic compile (read-only, no manager mutation)."""

from __future__ import annotations

from typing import Any

from continuity_state import (
    CanonAnchor,
    CharacterInterpretation,
    IssueState,
    PublicEvent,
)


def continuity_sequences_for_episodic(
    continuity_manager: Any | None,
) -> tuple[
    tuple[PublicEvent, ...],
    tuple[CharacterInterpretation, ...],
    tuple[IssueState, ...],
    tuple[CanonAnchor, ...],
]:
    """Return tuples suitable for ``get_or_compile_episodic_candidate_pool`` / snapshot key.

    Interpretations are flattened in sorted character-name order for stability.
    Issues and anchors are sorted by id.
    """
    if continuity_manager is None:
        return ((), (), (), ())
    mgr = continuity_manager
    events = tuple(getattr(mgr, "public_events", []) or ())
    interpretations_list: list[CharacterInterpretation] = []
    raw_interp = getattr(mgr, "interpretations", None) or {}
    for char_key in sorted(raw_interp.keys(), key=lambda k: str(k)):
        lst = raw_interp.get(char_key) or []
        interpretations_list.extend(lst)
    interpretations = tuple(interpretations_list)
    issues_raw = getattr(mgr, "issues", None) or {}
    if hasattr(issues_raw, "values"):
        issues_seq = tuple(
            sorted(issues_raw.values(), key=lambda i: str(getattr(i, "issue_id", "") or ""))
        )
    else:
        issues_seq = ()
    anchors_raw = list(getattr(mgr, "canon_anchors", []) or [])
    anchors = tuple(sorted(anchors_raw, key=lambda a: str(getattr(a, "anchor_id", "") or "")))
    return events, interpretations, issues_seq, anchors
