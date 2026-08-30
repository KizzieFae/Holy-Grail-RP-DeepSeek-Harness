"""Bounded semantic capture helpers for Plot Cognition forensics (#64)."""

from __future__ import annotations

from typing import Any

from .plot_cognition_semantic_authority import (
    DEFAULT_MAX_EVENT_SUMMARY_CHARS,
    DEFAULT_MAX_ISSUE_FIELD_CHARS,
    bounded_text,
    build_semantic_authority_excerpts,
)
from .plot_cognition_update_sources import build_plot_cognition_authority_projection
from .session_state import LiveSession
from .story_knowledge_contract import StoryKnowledgeRecord

DEFAULT_MAX_CANDIDATE_CHARS = 4000


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
    excerpts = build_semantic_authority_excerpts(
        fixture,
        through_domain_commit_id=through_domain_commit_id,
        max_event_summary_chars=max_event_summary_chars,
        max_issue_field_chars=max_issue_field_chars,
    )
    return {
        "canonical_projection": canonical,
        "public_events_verbatim": excerpts.get("public_events") or [],
        "issues_verbatim": excerpts.get("issues") or [],
        "semantic_authority_excerpts": excerpts,
        "truncation_policy": excerpts.get("truncation_policy") or {
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
                    "intended_direction": bounded_text(
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
                    "observation": bounded_text(
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
            "ensemble_context": bounded_text(
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
