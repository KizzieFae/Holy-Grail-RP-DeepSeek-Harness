"""Packaging join for authoritative issue pressure + B2 Librarian overlay (#40)."""

from __future__ import annotations

from typing import Any

from continuity_state import IssueState, IssueStatus

_PROJECTABLE_STATUSES = frozenset({IssueStatus.ACTIVE, IssueStatus.ESCALATING})
_SEMANTIC_OVERLAY_FIELDS = frozenset({"semantic_unmet_condition", "stakes_summary"})


def latest_player_authority_sequence_index(manager: Any) -> int:
    """Latest rp_history user-entry sequence_index recorded on the continuity manager."""
    return int(getattr(manager, "latest_player_authority_sequence_index", -1))


def note_authoritative_player_contribution(manager: Any, sequence_index: int) -> None:
    """Bind a newer tier-1 Player contribution for overlay freshness checks (#200)."""
    seq = int(sequence_index)
    if seq > latest_player_authority_sequence_index(manager):
        manager.latest_player_authority_sequence_index = seq


def overlay_semantic_fields_are_fresh(manager: Any, overlay: dict[str, Any]) -> bool:
    """True when no authoritative Player contribution occurred after overlay apply."""
    at_apply = int(overlay.get("player_authority_sequence_at_apply", -1))
    return latest_player_authority_sequence_index(manager) <= at_apply


def overlay_for_semantic_projection(
    manager: Any,
    overlay: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Return overlay suitable for objective semantic projection, or None if fully stale."""
    if overlay is None:
        return None
    if overlay_semantic_fields_are_fresh(manager, overlay):
        return overlay
    trimmed = {
        key: value
        for key, value in overlay.items()
        if key not in _SEMANTIC_OVERLAY_FIELDS
    }
    return trimmed or None


def compute_issue_material_fingerprint(issue: IssueState) -> str:
    participants = ",".join(sorted(str(p) for p in (issue.participants or []) if str(p).strip()))
    return "|".join(
        [
            str(issue.status.value),
            str(issue.pressure_kind or ""),
            str(issue.last_change or ""),
            participants,
        ]
    )


def get_projectable_issue_pressure_overlay(manager: Any, issue_id: str) -> dict[str, Any] | None:
    overlays = getattr(manager, "issue_pressure_semantic_overlays", None) or {}
    overlay = overlays.get(str(issue_id))
    if not isinstance(overlay, dict):
        return None
    if str(overlay.get("lifecycle", "")) != "active":
        return None
    issue = (getattr(manager, "issues", None) or {}).get(str(issue_id))
    if issue is None:
        return None
    if issue.status not in _PROJECTABLE_STATUSES:
        return None
    if str(overlay.get("issue_material_fingerprint", "")) != compute_issue_material_fingerprint(
        issue
    ):
        return None
    return overlay


def build_scene_pressure_entry(
    issue: IssueState,
    overlay: dict[str, Any] | None = None,
    *,
    manager: Any | None = None,
) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "issue_id": str(issue.issue_id),
        "status": issue.status.value,
        "participants": list(issue.participants),
        "last_change": issue.last_change,
        "pressure_kind": issue.pressure_kind,
        "blocked_what": issue.blocked_what,
        "required_next_step": issue.required_next_step,
        "description": issue.description,
    }
    effective_overlay = (
        overlay_for_semantic_projection(manager, overlay) if manager is not None else overlay
    )
    if effective_overlay:
        semantic = str(effective_overlay.get("semantic_unmet_condition", "") or "").strip()
        if semantic:
            entry["semantic_unmet_condition"] = semantic
            entry["semantic_authority"] = {
                "source": "librarian_overlay",
                "authority_class": "derived",
                "proposal_id": effective_overlay.get("proposal_id"),
                "domain_commit_id": effective_overlay.get("domain_commit_id"),
            }
        stakes = str(effective_overlay.get("stakes_summary", "") or "").strip()
        if stakes:
            entry["stakes_summary"] = stakes
            entry["stakes_authority"] = {
                "source": "librarian_overlay",
                "authority_class": "derived",
                "proposal_id": effective_overlay.get("proposal_id"),
                "domain_commit_id": effective_overlay.get("domain_commit_id"),
            }
    return entry
