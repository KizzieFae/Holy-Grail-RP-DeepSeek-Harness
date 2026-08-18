"""Lodging / sleeping-surface resolved outcome aspect (registry-owned)."""

from __future__ import annotations

from typing import Any

from continuity_state import IssueStatus

from resolved_outcome_normalize import _normalize_outcome_fragment, encode_slot_key
from resolved_outcome_spec import (
    AspectSpec,
    NormalizedCandidate,
    PromotionContext,
    PromotionDecision,
)

LODGING_SLEEP_SURFACE_ASPECT_ID = "lodging.sleep_surface"

SLEEPING_SURFACE_ISSUE_RULE_ID = "assignment.sleeping_surface.issue_resolved.v1"
SLEEPING_SURFACE_CONSEQUENCE_RULE_ID = "assignment.sleeping_surface.consequence.v1"
SLEEPING_SURFACE_ISSUE_PREFIX = "seed_sleeping_surface_assignment_"

_LODGING_SLEEP_SURFACE_REVOKE_SURFACE_ID = "unassigned"
FALLBACK_SLEEPING_SURFACE_IDS = frozenset({"floor", "couch", "cot", "unassigned"})


def get_valid_sleeping_surface_ids(scene_state: Any) -> set[str]:
    if isinstance(scene_state, dict):
        slots = scene_state.get("sleeping_surface_slots", [])
    else:
        slots = getattr(scene_state, "sleeping_surface_slots", []) if scene_state else []
    valid = {str(item).strip() for item in slots if str(item or "").strip()}
    valid.update(FALLBACK_SLEEPING_SURFACE_IDS)
    return valid


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


class LodgingSleepSurfacePromotionPolicy:
    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision:
        _ = candidate
        issue_id = _find_resolved_sleeping_surface_issue_id(ctx.manager, ctx.turn_index)
        if issue_id:
            return PromotionDecision(
                promote=True,
                source="issue_resolution",
                rule_id=SLEEPING_SURFACE_ISSUE_RULE_ID,
                issue_id=issue_id,
                reject_reason="",
                success_reason="promoted_issue_resolution",
            )
        if _has_strong_sleeping_surface_consequence(set(ctx.consequence_tags)):
            return PromotionDecision(
                promote=True,
                source="consequence",
                rule_id=SLEEPING_SURFACE_CONSEQUENCE_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_consequence",
            )
        return PromotionDecision(
            promote=False,
            source=None,
            rule_id="",
            issue_id=None,
            reject_reason="weak_signal",
            success_reason="",
        )


def _lodging_is_revocation(candidate: NormalizedCandidate) -> bool:
    return (
        str(candidate.value.get("surface_id", "") or "").strip()
        == _LODGING_SLEEP_SURFACE_REVOKE_SURFACE_ID
    )


def parse_lodging_sleep_surface_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[NormalizedCandidate], str]:
    if not isinstance(move, dict):
        return [], "no_candidate"
    updates = move.get("scene_state_updates", {})
    if not isinstance(updates, dict):
        return [], "no_candidate"

    raw = updates.get("sleeping_surface_assignment")
    raw_candidates: list[Any] = []
    if isinstance(raw, dict):
        raw_candidates.append(raw)
    elif isinstance(raw, list):
        raw_candidates.extend(raw)
    if not raw_candidates:
        return [], "no_candidate"

    valid_surface_ids = get_valid_sleeping_surface_ids(scene_state)
    normalized: list[dict[str, str]] = []
    saw_invalid_surface = False
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        assignee_id = str(item.get("assignee_id", item.get("assignee", "")) or "").strip()
        surface_id = str(item.get("surface_id", item.get("surface", "")) or "").strip()
        if not assignee_id or not surface_id:
            continue
        if surface_id not in valid_surface_ids:
            saw_invalid_surface = True
            continue
        row = {"assignee_id": assignee_id, "surface_id": surface_id}
        if row not in normalized:
            normalized.append(row)

    if not normalized:
        if saw_invalid_surface:
            return [], "invalid_surface_id"
        return [], "no_candidate"

    return (
        [
            NormalizedCandidate(
                aspect_id=LODGING_SLEEP_SURFACE_ASPECT_ID,
                subject_id=row["assignee_id"],
                value={"assignee_id": row["assignee_id"], "surface_id": row["surface_id"]},
            )
            for row in normalized
        ],
        "",
    )


def _lodging_slot_key_fn(candidate: NormalizedCandidate) -> str:
    return encode_slot_key(candidate.aspect_id, candidate.subject_id)


def _lodging_build_outcome_id(
    candidate: NormalizedCandidate, turn_index: int, source_event_id: str
) -> str:
    event_fragment = _normalize_outcome_fragment(source_event_id or f"turn_{turn_index}")
    assignee_fragment = _normalize_outcome_fragment(candidate.subject_id)
    surface_fragment = _normalize_outcome_fragment(candidate.value.get("surface_id", ""))
    return (
        f"resolved_assignment_sleeping_surface_{assignee_fragment}_"
        f"{surface_fragment}_{event_fragment}"
    )


LODGING_SLEEP_SURFACE_SPEC = AspectSpec(
    aspect_id=LODGING_SLEEP_SURFACE_ASPECT_ID,
    outcome_class="assignment",
    legacy_category="assignment",
    legacy_key="sleeping_surface",
    parse_candidates=parse_lodging_sleep_surface_candidates,
    slot_key_fn=_lodging_slot_key_fn,
    build_outcome_id=_lodging_build_outcome_id,
    is_revocation=_lodging_is_revocation,
    promotion_policy=LodgingSleepSurfacePromotionPolicy(),
    superseded_reason="superseded_by_reassignment",
    revoked_reason="revoked_unassigned",
    conflicting_candidates_reason="competing_same_turn_assignment",
)
