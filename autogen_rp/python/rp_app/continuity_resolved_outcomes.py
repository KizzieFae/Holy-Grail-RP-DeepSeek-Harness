import re
from typing import Any

from continuity_state import IssueStatus, ResolvedOutcome

FALLBACK_SLEEPING_SURFACE_IDS = frozenset({"floor", "couch", "cot", "unassigned"})
SLEEPING_SURFACE_ISSUE_RULE_ID = "assignment.sleeping_surface.issue_resolved.v1"
SLEEPING_SURFACE_CONSEQUENCE_RULE_ID = "assignment.sleeping_surface.consequence.v1"
SLEEPING_SURFACE_ISSUE_PREFIX = "seed_sleeping_surface_assignment_"


def get_valid_sleeping_surface_ids(scene_state: Any) -> set[str]:
    if isinstance(scene_state, dict):
        slots = scene_state.get("sleeping_surface_slots", [])
    else:
        slots = getattr(scene_state, "sleeping_surface_slots", []) if scene_state else []
    valid = {str(item).strip() for item in slots if str(item or "").strip()}
    valid.update(FALLBACK_SLEEPING_SURFACE_IDS)
    return valid


def extract_sleeping_surface_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[dict[str, str]], str]:
    if not isinstance(move, dict):
        return [], "no_candidate"
    updates = move.get("scene_state_updates", {})
    if not isinstance(updates, dict):
        return [], "no_candidate"

    raw_candidates: list[Any] = []
    for key in ("sleeping_surface_assignment", "sleeping_surface_assignments"):
        raw = updates.get(key)
        if isinstance(raw, dict):
            raw_candidates.append(raw)
        elif isinstance(raw, list):
            raw_candidates.extend(raw)

    if not raw_candidates:
        return [], "no_candidate"

    valid_surface_ids = get_valid_sleeping_surface_ids(scene_state)
    normalized: list[dict[str, str]] = []
    saw_invalid_surface = False
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            continue
        assignee_id = str(
            raw.get("assignee_id", raw.get("assignee", "")) or ""
        ).strip()
        surface_id = str(raw.get("surface_id", raw.get("surface", "")) or "").strip()
        if not assignee_id or not surface_id:
            continue
        if surface_id not in valid_surface_ids:
            saw_invalid_surface = True
            continue
        candidate = {
            "assignee_id": assignee_id,
            "surface_id": surface_id,
        }
        if candidate not in normalized:
            normalized.append(candidate)

    if normalized:
        return normalized, ""
    if saw_invalid_surface:
        return [], "invalid_surface_id"
    return [], "no_candidate"


def build_sleeping_surface_state_change(move: dict[str, Any], scene_state: Any) -> str:
    candidates, _ = extract_sleeping_surface_candidates(move, scene_state)
    if len(candidates) != 1:
        return ""
    candidate = candidates[0]
    return (
        f"{candidate['assignee_id']} sleeping assignment set to "
        f"{candidate['surface_id']}."
    )


def _is_sleeping_surface_issue(issue: Any) -> bool:
    issue_id = str(getattr(issue, "issue_id", "") or "")
    if issue_id.startswith(SLEEPING_SURFACE_ISSUE_PREFIX):
        return True
    text_parts = [
        str(getattr(issue, "description", "") or ""),
        *(str(item) for item in getattr(issue, "resolution_signals", []) or []),
        *(str(item) for item in getattr(issue, "escalation_signals", []) or []),
    ]
    blob = " ".join(text_parts).lower()
    return any(
        token in blob
        for token in ("sleep", "bunk", "bed", "couch", "cot", "floor", "roommate")
    )


def _find_resolved_sleeping_surface_issue_id(manager: Any, turn_index: int) -> str | None:
    matches = [
        str(issue.issue_id)
        for issue in getattr(manager, "issues", {}).values()
        if getattr(issue, "status", None) == IssueStatus.RESOLVED
        and getattr(issue, "last_turn_index", None) == turn_index
        and _is_sleeping_surface_issue(issue)
    ]
    if not matches:
        return None
    return sorted(matches)[0]


def _has_strong_sleeping_surface_consequence(consequence_tags: set[str]) -> bool:
    tags = {str(item or "").strip() for item in consequence_tags if str(item or "").strip()}
    if "refusal" in tags:
        return False
    if {"commitment", "plan_committed", "decision_made"}.intersection(tags):
        return True
    return "agreement" in tags


def _find_active_sleeping_surface_outcome(
    manager: Any, assignee_id: str
) -> ResolvedOutcome | None:
    for outcome in reversed(getattr(manager, "resolved_outcomes", [])):
        if (
            outcome.category == "assignment"
            and outcome.key == "sleeping_surface"
            and outcome.subject_id == assignee_id
            and outcome.status == "active"
        ):
            return outcome
    return None


def _normalize_outcome_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_") or "x"


def _build_outcome_id(
    assignee_id: str, surface_id: str, turn_index: int, source_event_id: str
) -> str:
    event_fragment = _normalize_outcome_fragment(source_event_id or f"turn_{turn_index}")
    assignee_fragment = _normalize_outcome_fragment(assignee_id)
    surface_fragment = _normalize_outcome_fragment(surface_id)
    return (
        f"resolved_assignment_sleeping_surface_{assignee_fragment}_"
        f"{surface_fragment}_{event_fragment}"
    )


def apply_sleeping_surface_outcome_updates(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, Any]:
    candidates, reason = extract_sleeping_surface_candidates(move, getattr(manager, "scene_state", None))
    debug: dict[str, Any] = {
        "candidate": candidates[0] if len(candidates) == 1 else None,
        "candidate_source": None,
        "decision": "none",
        "reason": reason or "no_candidate",
        "outcome_id": None,
        "supersedes_outcome_id": None,
        "issue_id": None,
    }
    if not candidates:
        return debug

    if len(candidates) > 1:
        assignee_to_surface: dict[str, str] = {}
        for candidate in candidates:
            assignee_id = candidate["assignee_id"]
            surface_id = candidate["surface_id"]
            previous_surface = assignee_to_surface.get(assignee_id)
            if previous_surface and previous_surface != surface_id:
                debug["reason"] = "competing_same_turn_assignment"
                return debug
            assignee_to_surface[assignee_id] = surface_id
        debug["reason"] = "multiple_candidates_unsupported"
        return debug

    candidate = candidates[0]
    assignee_id = candidate["assignee_id"]
    surface_id = candidate["surface_id"]
    consequence_tags = {
        str(item) for item in turn_consequences.get("tags", []) if str(item).strip()
    }
    issue_id = _find_resolved_sleeping_surface_issue_id(manager, turn_index)
    if issue_id:
        debug["candidate_source"] = "issue_resolution"
        debug["issue_id"] = issue_id
        rule_id = SLEEPING_SURFACE_ISSUE_RULE_ID
    elif _has_strong_sleeping_surface_consequence(consequence_tags):
        debug["candidate_source"] = "consequence"
        rule_id = SLEEPING_SURFACE_CONSEQUENCE_RULE_ID
    else:
        debug["reason"] = "weak_signal"
        return debug

    active = _find_active_sleeping_surface_outcome(manager, assignee_id)
    if surface_id == "unassigned":
        if active is None:
            debug["reason"] = "no_active_outcome_to_revoke"
            return debug
        active.status = "revoked"
        active.revoked_turn_index = turn_index
        debug["decision"] = "revoked"
        debug["reason"] = "revoked_unassigned"
        debug["outcome_id"] = active.outcome_id
        return debug

    if active is not None and active.value.get("surface_id") == surface_id:
        debug["reason"] = "same_assignment_already_active"
        debug["outcome_id"] = active.outcome_id
        return debug

    source_event_id = str(getattr(event, "event_id", "") or "")
    outcome = ResolvedOutcome(
        outcome_id=_build_outcome_id(assignee_id, surface_id, turn_index, source_event_id),
        category="assignment",
        key="sleeping_surface",
        subject_id=assignee_id,
        value={
            "assignee_id": assignee_id,
            "surface_id": surface_id,
        },
        status="active",
        source_event_id=source_event_id,
        source_issue_id=issue_id,
        rule_id=rule_id,
        supersedes_outcome_id=active.outcome_id if active is not None else None,
        created_turn_index=turn_index,
    )
    if active is not None:
        active.status = "superseded"
        active.superseded_turn_index = turn_index
    getattr(manager, "resolved_outcomes", []).append(outcome)
    debug["decision"] = "superseded" if active is not None else "promoted"
    debug["reason"] = (
        "superseded_by_reassignment" if active is not None else (
            "promoted_issue_resolution" if issue_id else "promoted_consequence"
        )
    )
    debug["outcome_id"] = outcome.outcome_id
    debug["supersedes_outcome_id"] = outcome.supersedes_outcome_id
    return debug
