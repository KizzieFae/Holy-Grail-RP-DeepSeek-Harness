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
    Issues use ``ContinuityManager.get_active_issues(limit=0, participants=None)`` — the same
    projection as authoritative ACTIVE ISSUES (``scene_state.active_issue_ids`` + default status
    filter), not the full ``manager.issues`` map. Sorted by issue id for stability.
    Anchors are sorted by id.
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
    get_active = getattr(mgr, "get_active_issues", None)
    if callable(get_active):
        active_issues = get_active(limit=0, participants=None)
        issues_seq = tuple(
            sorted(
                active_issues,
                key=lambda i: str(getattr(i, "issue_id", "") or ""),
            )
        )
    else:
        issues_seq = ()
    anchors_raw = list(getattr(mgr, "canon_anchors", []) or [])
    anchors = tuple(sorted(anchors_raw, key=lambda a: str(getattr(a, "anchor_id", "") or "")))
    return events, interpretations, issues_seq, anchors
