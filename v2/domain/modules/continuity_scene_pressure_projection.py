"""Packaging join for authoritative issue pressure + B2 Librarian overlay (#40)."""

from __future__ import annotations

from typing import Any

from continuity_state import IssueState, IssueStatus

_PROJECTABLE_STATUSES = frozenset({IssueStatus.ACTIVE, IssueStatus.ESCALATING})


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
    if overlay:
        entry["semantic_unmet_condition"] = str(overlay.get("semantic_unmet_condition", "") or "")
        entry["semantic_authority"] = {
            "source": "librarian_overlay",
            "authority_class": "derived",
            "proposal_id": overlay.get("proposal_id"),
            "domain_commit_id": overlay.get("domain_commit_id"),
        }
        stakes = str(overlay.get("stakes_summary", "") or "").strip()
        if stakes:
            entry["stakes_summary"] = stakes
            entry["stakes_authority"] = {
                "source": "librarian_overlay",
                "authority_class": "derived",
                "proposal_id": overlay.get("proposal_id"),
                "domain_commit_id": overlay.get("domain_commit_id"),
            }
    return entry
