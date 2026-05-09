"""Access / location-entry resolved outcome aspect (registry-owned)."""

from __future__ import annotations

from typing import Any

from resolved_outcome_normalize import _normalize_outcome_fragment
from resolved_outcome_spec import (
    AspectSpec,
    NormalizedCandidate,
    PromotionContext,
    PromotionDecision,
)

ACCESS_LOCATION_ENTRY_ASPECT_ID = "access.location_entry"

ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID = "access.location_entry.allowed.v1"
ACCESS_LOCATION_ENTRY_DENIED_RULE_ID = "access.location_entry.denied.v1"

LOCATION_ENTRY_STATUSES = frozenset({"allowed", "denied"})


def get_valid_location_entry_ids(scene_state: Any) -> set[str]:
    if isinstance(scene_state, dict):
        slots = scene_state.get("location_entry_slots", [])
    else:
        slots = getattr(scene_state, "location_entry_slots", []) if scene_state else []
    return {str(item).strip() for item in slots if str(item or "").strip()}


class AccessLocationEntryPromotionPolicy:
    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision:
        _ = ctx
        status = str(candidate.value.get("status", "") or "").strip()
        if status == "allowed":
            return PromotionDecision(
                promote=True,
                source="structured_permission",
                rule_id=ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_structured_permission",
            )
        if status == "denied":
            return PromotionDecision(
                promote=True,
                source="structured_permission",
                rule_id=ACCESS_LOCATION_ENTRY_DENIED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_structured_permission",
            )
        return PromotionDecision(
            promote=False,
            source=None,
            rule_id="",
            issue_id=None,
            reject_reason="weak_signal",
            success_reason="",
        )


def parse_location_entry_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[NormalizedCandidate], str]:
    if not isinstance(move, dict):
        return [], "no_candidate"
    updates = move.get("scene_state_updates", {})
    if not isinstance(updates, dict):
        return [], "no_candidate"

    raw = updates.get("location_entry_outcome")
    raw_candidates: list[Any] = []
    if isinstance(raw, dict):
        raw_candidates.append(raw)
    elif isinstance(raw, list):
        raw_candidates.extend(raw)
    if not raw_candidates:
        return [], "no_candidate"

    valid_location_ids = get_valid_location_entry_ids(scene_state)
    normalized: list[dict[str, str]] = []
    saw_invalid_location = False
    saw_invalid_status = False
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        subject_id = str(item.get("subject_id", item.get("subject", "")) or "").strip()
        location_id = str(
            item.get("location_id", item.get("location", "")) or ""
        ).strip()
        status = str(item.get("status", "") or "").strip().lower()
        if not subject_id or not location_id or not status:
            continue
        if location_id not in valid_location_ids:
            saw_invalid_location = True
            continue
        if status not in LOCATION_ENTRY_STATUSES:
            saw_invalid_status = True
            continue
        row = {
            "subject_id": subject_id,
            "location_id": location_id,
            "status": status,
        }
        if row not in normalized:
            normalized.append(row)

    if not normalized:
        if saw_invalid_location:
            return [], "invalid_location_id"
        if saw_invalid_status:
            return [], "invalid_status"
        return [], "no_candidate"

    return (
        [
            NormalizedCandidate(
                aspect_id=ACCESS_LOCATION_ENTRY_ASPECT_ID,
                subject_id=row["subject_id"],
                value={
                    "location_id": row["location_id"],
                    "status": row["status"],
                },
            )
            for row in normalized
        ],
        "",
    )


def _location_entry_slot_key_fn(candidate: NormalizedCandidate) -> str:
    location_id = str(candidate.value.get("location_id", "") or "").strip()
    return f"{candidate.aspect_id}::{candidate.subject_id}::{location_id}"


def _location_entry_build_outcome_id(
    candidate: NormalizedCandidate, turn_index: int, source_event_id: str
) -> str:
    event_fragment = _normalize_outcome_fragment(source_event_id or f"turn_{turn_index}")
    subject_fragment = _normalize_outcome_fragment(candidate.subject_id)
    location_fragment = _normalize_outcome_fragment(candidate.value.get("location_id", ""))
    status_fragment = _normalize_outcome_fragment(candidate.value.get("status", ""))
    return (
        "resolved_access_location_entry_"
        f"{subject_fragment}_{location_fragment}_{status_fragment}_{event_fragment}"
    )


def _location_entry_is_revocation(candidate: NormalizedCandidate) -> bool:
    _ = candidate
    return False


ACCESS_LOCATION_ENTRY_SPEC = AspectSpec(
    aspect_id=ACCESS_LOCATION_ENTRY_ASPECT_ID,
    outcome_class="access",
    legacy_category="access",
    legacy_key="location_entry",
    parse_candidates=parse_location_entry_outcome_candidates,
    slot_key_fn=_location_entry_slot_key_fn,
    build_outcome_id=_location_entry_build_outcome_id,
    is_revocation=_location_entry_is_revocation,
    promotion_policy=AccessLocationEntryPromotionPolicy(),
    superseded_reason="superseded_permission_state",
    revoked_reason="revoked",
    conflicting_candidates_reason="competing_same_turn_location_entry",
)
