"""Bounded semantic capture helpers for Plot Cognition forensics (#64)."""

from __future__ import annotations

from typing import Any

from .plot_cognition_update_sources import build_plot_cognition_authority_projection
from .session_state import LiveSession
from .story_knowledge_contract import StoryKnowledgeRecord

DEFAULT_MAX_EVENT_SUMMARY_CHARS = 500
DEFAULT_MAX_ISSUE_FIELD_CHARS = 400
DEFAULT_MAX_CANDIDATE_CHARS = 4000


def _bounded_text(value: str | None, *, max_chars: int) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def capture_authority_projection_verbatim(
    fixture: LiveSession,
    story_records: list[StoryKnowledgeRecord] | None,
    through_domain_commit_id: str | None,
    *,
    max_event_summary_chars: int = DEFAULT_MAX_EVENT_SUMMARY_CHARS,
    max_issue_field_chars: int = DEFAULT_MAX_ISSUE_FIELD_CHARS,
) -> dict[str, Any]:
    """Capture bounded verbatim authority material used at decision time."""
    canonical = build_plot_cognition_authority_projection(
        fixture,
        story_records,
        through_domain_commit_id,
    )
    public_events: list[dict[str, Any]] = []
    mgr = fixture.manager
    through_turn = None
    if through_domain_commit_id:
        from .plot_cognition_update_sources import _through_continuity_turn_index

        through_turn = _through_continuity_turn_index(fixture, through_domain_commit_id)
    for event in getattr(mgr, "public_events", []) or []:
        turn_index = getattr(event, "turn_index", None)
        if through_turn is not None and turn_index is not None and int(turn_index) > through_turn:
            continue
        public_events.append(
            {
                "event_id": str(getattr(event, "event_id", "") or ""),
                "turn_index": turn_index,
                "event_type": str(getattr(event, "event_type", "") or ""),
                "summary": _bounded_text(
                    str(getattr(event, "summary", "") or getattr(event, "description", "") or ""),
                    max_chars=max_event_summary_chars,
                ),
            }
        )
    issues: list[dict[str, Any]] = []
    issue_map = getattr(mgr, "issues", {}) or {}
    active_ids = list(getattr(mgr.scene_state, "active_issue_ids", None) or [])
    for issue_id in sorted(active_ids):
        issue = issue_map.get(issue_id)
        if issue is None:
            continue
        issues.append(
            {
                "issue_id": str(issue.issue_id),
                "status": str(getattr(issue.status, "value", issue.status)),
                "description": _bounded_text(
                    str(getattr(issue, "description", "") or ""),
                    max_chars=max_issue_field_chars,
                ),
                "blocked_what": _bounded_text(
                    str(getattr(issue, "blocked_what", "") or ""),
                    max_chars=max_issue_field_chars,
                ),
                "required_next_step": _bounded_text(
                    str(getattr(issue, "required_next_step", "") or ""),
                    max_chars=max_issue_field_chars,
                ),
            }
        )
    return {
        "canonical_projection": canonical,
        "public_events_verbatim": public_events,
        "issues_verbatim": issues,
        "truncation_policy": {
            "max_event_summary_chars": max_event_summary_chars,
            "max_issue_field_chars": max_issue_field_chars,
        },
    }


def capture_epistemic_envelope(envelope: Any) -> dict[str, Any]:
    if hasattr(envelope, "to_dict"):
        return envelope.to_dict()
    if isinstance(envelope, dict):
        return dict(envelope)
    return {"value": str(envelope)}


def bounded_overlay_snapshot(store_dict: dict[str, Any] | None) -> dict[str, Any]:
    if not store_dict:
        return {}
    goals = []
    for goal in (store_dict.get("goals") or {}).values():
        if isinstance(goal, dict):
            goals.append(
                {
                    "goal_id": goal.get("goal_id"),
                    "intended_direction": _bounded_text(
                        str(goal.get("intended_direction", "")),
                        max_chars=DEFAULT_MAX_CANDIDATE_CHARS,
                    ),
                    "activity_state": goal.get("activity_state"),
                }
            )
    pressures = []
    for pressure in (store_dict.get("pressures") or {}).values():
        if isinstance(pressure, dict):
            pressures.append(
                {
                    "pressure_id": pressure.get("pressure_id"),
                    "observation": _bounded_text(
                        str(pressure.get("observation", "")),
                        max_chars=DEFAULT_MAX_CANDIDATE_CHARS,
                    ),
                    "activity_state": pressure.get("activity_state"),
                }
            )
    frame = store_dict.get("global_plot_frame")
    frame_snapshot = None
    if isinstance(frame, dict):
        frame_snapshot = {
            "frame_id": frame.get("frame_id"),
            "ensemble_context": _bounded_text(
                str(frame.get("ensemble_context", "")),
                max_chars=DEFAULT_MAX_CANDIDATE_CHARS,
            ),
            "activity_state": frame.get("activity_state"),
        }
    return {
        "store_revision": store_dict.get("store_revision"),
        "goals": goals,
        "pressures": pressures,
        "global_plot_frame": frame_snapshot,
    }
