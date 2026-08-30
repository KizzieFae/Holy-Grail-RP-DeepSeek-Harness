"""Bounded verbatim semantic authority excerpts for Plot Cognition update (#65).

Transport-only projection of existing authoritative Continuity text alongside digest
identity fields. Not included in authority_source_fingerprint (see gather_update_source_snapshot).
"""

from __future__ import annotations

from typing import Any

from .session_state import LiveSession

SEMANTIC_AUTHORITY_EXCERPTS_SCHEMA = "hg_plot_cognition_semantic_authority_excerpts_v1"

DEFAULT_MAX_EVENT_SUMMARY_CHARS = 500
DEFAULT_MAX_ISSUE_FIELD_CHARS = 400
DEFAULT_MAX_GROUNDING_STATEMENT_CHARS = 400
DEFAULT_MAX_MOVE_EXCERPT_CHARS = 600


def bounded_text(value: str | None, *, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def _find_committed_move(fixture: LiveSession, domain_commit_id: str) -> dict[str, Any] | None:
    target = str(domain_commit_id or "").strip()
    if not target:
        return None
    for rnd in fixture.rounds:
        for turn in rnd.character_turns:
            if str(turn.domain_commit_id or "") == target:
                move = turn.committed_move
                return dict(move) if isinstance(move, dict) else None
        if str(rnd.domain_commit_id or "") == target:
            move = rnd.committed_move
            return dict(move) if isinstance(move, dict) else None
    return None


def extract_bounded_move_excerpt(committed_move: Any, *, max_chars: int = DEFAULT_MAX_MOVE_EXCERPT_CHARS) -> str:
    if not isinstance(committed_move, dict):
        return ""
    parts: list[str] = []
    for beat in committed_move.get("beats") or []:
        if not isinstance(beat, dict):
            continue
        beat_type = str(beat.get("type") or "").strip().lower()
        if beat_type == "dialogue":
            dialogue = str(beat.get("dialogue") or "").strip()
            if dialogue:
                parts.append(dialogue)
        elif beat_type == "action":
            action = str(beat.get("action") or "").strip()
            if action:
                parts.append(action)
    motivation = committed_move.get("motivation")
    if isinstance(motivation, dict):
        goal = str(motivation.get("goal") or "").strip()
        if goal and not parts:
            parts.append(goal)
    return bounded_text(" | ".join(parts), max_chars=max_chars)


def build_semantic_authority_excerpts(
    fixture: LiveSession,
    *,
    through_domain_commit_id: str | None,
    max_event_summary_chars: int = DEFAULT_MAX_EVENT_SUMMARY_CHARS,
    max_issue_field_chars: int = DEFAULT_MAX_ISSUE_FIELD_CHARS,
    max_grounding_statement_chars: int = DEFAULT_MAX_GROUNDING_STATEMENT_CHARS,
    max_move_excerpt_chars: int = DEFAULT_MAX_MOVE_EXCERPT_CHARS,
) -> dict[str, Any]:
    from .plot_cognition_update_sources import _through_continuity_turn_index
    from scene_grounding import rebuild_scene_grounding_from_continuity

    mgr = fixture.manager
    through_turn = _through_continuity_turn_index(fixture, through_domain_commit_id)

    public_events: list[dict[str, Any]] = []
    for event in getattr(mgr, "public_events", []) or []:
        turn_index = getattr(event, "turn_index", None)
        if through_turn is not None and turn_index is not None and int(turn_index) > through_turn:
            continue
        summary = bounded_text(
            str(getattr(event, "summary", "") or getattr(event, "description", "") or ""),
            max_chars=max_event_summary_chars,
        )
        if not summary:
            continue
        public_events.append(
            {
                "event_id": str(getattr(event, "event_id", "") or ""),
                "turn_index": turn_index,
                "event_type": str(getattr(event, "event_type", "") or ""),
                "summary": summary,
            }
        )

    issues: list[dict[str, Any]] = []
    issue_map = getattr(mgr, "issues", {}) or {}
    active_ids = list(getattr(mgr.scene_state, "active_issue_ids", None) or [])
    for issue_id in sorted(active_ids):
        issue = issue_map.get(issue_id)
        if issue is None:
            continue
        description = bounded_text(
            str(getattr(issue, "description", "") or ""),
            max_chars=max_issue_field_chars,
        )
        blocked_what = bounded_text(
            str(getattr(issue, "blocked_what", "") or ""),
            max_chars=max_issue_field_chars,
        )
        required_next_step = bounded_text(
            str(getattr(issue, "required_next_step", "") or ""),
            max_chars=max_issue_field_chars,
        )
        if not any((description, blocked_what, required_next_step)):
            continue
        issues.append(
            {
                "issue_id": str(issue.issue_id),
                "status": str(getattr(issue.status, "value", issue.status)),
                "description": description,
                "blocked_what": blocked_what,
                "required_next_step": required_next_step,
            }
        )

    grounding = rebuild_scene_grounding_from_continuity(mgr)
    scene_grounding_facts: list[dict[str, Any]] = []
    for item in grounding.get("facts") or []:
        if not isinstance(item, dict):
            continue
        statement = bounded_text(
            str(item.get("statement") or ""),
            max_chars=max_grounding_statement_chars,
        )
        if not statement:
            continue
        scene_grounding_facts.append(
            {
                "fact_id": str(item.get("fact_id", "")),
                "statement": statement,
            }
        )

    committed_moves: list[dict[str, Any]] = []
    event_turns = {
        int(item["turn_index"])
        for item in public_events
        if item.get("turn_index") is not None
    }
    from .plot_cognition_update_sources import _committed_move_digests

    for item in _committed_move_digests(
        fixture,
        through_domain_commit_id=through_domain_commit_id,
    ):
        turn_index = item.get("continuity_turn_index")
        if turn_index is not None and int(turn_index) in event_turns:
            continue
        commit_id = str(item.get("domain_commit_id") or "")
        move = _find_committed_move(fixture, commit_id)
        excerpt = extract_bounded_move_excerpt(move, max_chars=max_move_excerpt_chars)
        if not excerpt:
            continue
        committed_moves.append(
            {
                "domain_commit_id": commit_id,
                "character_id": item.get("character_id"),
                "continuity_turn_index": turn_index,
                "bounded_excerpt": excerpt,
            }
        )

    return {
        "schema": SEMANTIC_AUTHORITY_EXCERPTS_SCHEMA,
        "public_events": public_events,
        "issues": issues,
        "scene_grounding_facts": scene_grounding_facts,
        "committed_moves": committed_moves,
        "truncation_policy": {
            "max_event_summary_chars": max_event_summary_chars,
            "max_issue_field_chars": max_issue_field_chars,
            "max_grounding_statement_chars": max_grounding_statement_chars,
            "max_move_excerpt_chars": max_move_excerpt_chars,
        },
    }
