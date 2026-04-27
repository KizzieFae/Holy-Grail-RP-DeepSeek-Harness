"""Registry for resolved continuity outcomes (aspect-scoped, deterministic).

`ResolvedOutcome` rows (see `continuity_state`) are **slot-scoped** continuity facts: row
`status` is `active` / `superseded` / `revoked`; **domain** state (e.g. transactional
**phase** for `transaction.scene_commitment`, GitHub #127) lives in `value`, not the
English word *resolved* on the type name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from continuity_state import IssueStatus

LODGING_SLEEP_SURFACE_ASPECT_ID = "lodging.sleep_surface"
COMMUNICATION_HOUSING_CALL_ASPECT_ID = "communication.housing_call"
MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID = "medical.suppressant_formulation"
ACCESS_LOCATION_ENTRY_ASPECT_ID = "access.location_entry"
TRANSACTION_SCENE_COMMITMENT_ASPECT_ID = "transaction.scene_commitment"

SLEEPING_SURFACE_ISSUE_RULE_ID = "assignment.sleeping_surface.issue_resolved.v1"
SLEEPING_SURFACE_CONSEQUENCE_RULE_ID = "assignment.sleeping_surface.consequence.v1"
SLEEPING_SURFACE_ISSUE_PREFIX = "seed_sleeping_surface_assignment_"

HOUSING_CALL_ISSUE_RULE_ID = "communication.housing_call.issue_resolved.v1"
HOUSING_CALL_COMPLETED_RULE_ID = "communication.housing_call.completed.v1"
HOUSING_CALL_FAILED_RULE_ID = "communication.housing_call.failed.v1"

SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID = (
    "medical.suppressant_formulation.compatible.v1"
)
SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID = (
    "medical.suppressant_formulation.incompatible.v1"
)
ACCESS_LOCATION_ENTRY_ALLOWED_RULE_ID = "access.location_entry.allowed.v1"
ACCESS_LOCATION_ENTRY_DENIED_RULE_ID = "access.location_entry.denied.v1"

SCENE_COMMITMENT_COMMITTED_RULE_ID = "transaction.scene_commitment.committed.v1"
SCENE_COMMITMENT_AWAITING_RULE_ID = "transaction.scene_commitment.awaiting_fulfillment.v1"
SCENE_COMMITMENT_FULFILLED_RULE_ID = "transaction.scene_commitment.fulfilled.v1"
SCENE_COMMITMENT_FAILED_RULE_ID = "transaction.scene_commitment.failed.v1"

_LODGING_SLEEP_SURFACE_REVOKE_SURFACE_ID = "unassigned"
FALLBACK_SLEEPING_SURFACE_IDS = frozenset({"floor", "couch", "cot", "unassigned"})
HOUSING_CALL_TERMINAL_STATUSES = frozenset({"completed", "failed"})
SUPPRESSANT_FORMULATION_STATUSES = frozenset({"compatible", "incompatible"})
LOCATION_ENTRY_STATUSES = frozenset({"allowed", "denied"})

# Issue #127 — transactional scene commitments (semantic slot: kind::subject_scope).
SCENE_COMMITMENT_KINDS = frozenset(
    {"food_order", "ride", "payment", "generic"}
)
# `initiated` is schema-valid; MVP promotion deferred until deterministic signals exist.
SCENE_COMMITMENT_PHASES = frozenset(
    {
        "initiated",
        "committed",
        "awaiting_fulfillment",
        "fulfilled",
        "failed",
        "voided",
    }
)


def get_valid_sleeping_surface_ids(scene_state: Any) -> set[str]:
    if isinstance(scene_state, dict):
        slots = scene_state.get("sleeping_surface_slots", [])
    else:
        slots = getattr(scene_state, "sleeping_surface_slots", []) if scene_state else []
    valid = {str(item).strip() for item in slots if str(item or "").strip()}
    valid.update(FALLBACK_SLEEPING_SURFACE_IDS)
    return valid


def get_valid_location_entry_ids(scene_state: Any) -> set[str]:
    if isinstance(scene_state, dict):
        slots = scene_state.get("location_entry_slots", [])
    else:
        slots = getattr(scene_state, "location_entry_slots", []) if scene_state else []
    return {str(item).strip() for item in slots if str(item or "").strip()}


def encode_slot_key(aspect_id: str, subject_id: str) -> str:
    return f"{aspect_id}::{subject_id}"


def _normalize_scene_commitment_token(s: str, *, max_len: int = 64) -> str:
    t = re.sub(r"[^a-z0-9_:]+", "_", str(s or "").lower().strip()).strip("_")
    if len(t) > max_len:
        t = t[:max_len].rstrip("_")
    return t or "x"


def _normalize_outcome_fragment(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_") or "x"


@dataclass(frozen=True)
class NormalizedCandidate:
    aspect_id: str
    subject_id: str
    value: dict[str, str]


@dataclass(frozen=True)
class PromotionContext:
    """Read-only context for promotion_policy.evaluate (do not mutate manager)."""

    turn_index: int
    consequence_tags: frozenset[str]
    manager: Any


@dataclass(frozen=True)
class PromotionDecision:
    promote: bool
    source: str | None
    rule_id: str
    issue_id: str | None
    reject_reason: str
    success_reason: str


class PromotionPolicy(Protocol):
    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision: ...


@dataclass(frozen=True)
class AspectSpec:
    aspect_id: str
    outcome_class: str
    legacy_category: str
    legacy_key: str
    parse_candidates: Callable[[dict[str, Any], Any], tuple[list[NormalizedCandidate], str]]
    slot_key_fn: Callable[[NormalizedCandidate], str]
    build_outcome_id: Callable[[NormalizedCandidate, int, str], str]
    is_revocation: Callable[[NormalizedCandidate], bool]
    promotion_policy: PromotionPolicy
    superseded_reason: str
    revoked_reason: str
    conflicting_candidates_reason: str = "multiple_candidates_unsupported"


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


def _is_housing_call_issue(issue: Any) -> bool:
    text_parts = [
        str(getattr(issue, "issue_id", "") or ""),
        str(getattr(issue, "description", "") or ""),
        *(str(item) for item in getattr(issue, "resolution_signals", []) or []),
        *(str(item) for item in getattr(issue, "escalation_signals", []) or []),
    ]
    blob = " ".join(text_parts).lower()
    return any(
        token in blob
        for token in (
            "housing call",
            "call housing",
            "res life",
            "res-life",
            "residence life",
            "housing office",
        )
    )


def _find_resolved_housing_call_issue_id(manager: Any, turn_index: int) -> str | None:
    matches = [
        str(issue.issue_id)
        for issue in getattr(manager, "issues", {}).values()
        if getattr(issue, "status", None) == IssueStatus.RESOLVED
        and getattr(issue, "last_turn_index", None) == turn_index
        and _is_housing_call_issue(issue)
    ]
    if not matches:
        return None
    return sorted(matches)[0]


class CommunicationHousingCallPromotionPolicy:
    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision:
        issue_id = _find_resolved_housing_call_issue_id(ctx.manager, ctx.turn_index)
        if issue_id:
            return PromotionDecision(
                promote=True,
                source="issue_resolution",
                rule_id=HOUSING_CALL_ISSUE_RULE_ID,
                issue_id=issue_id,
                reject_reason="",
                success_reason="promoted_issue_resolution",
            )
        status = str(candidate.value.get("status", "") or "").strip()
        if status == "completed":
            return PromotionDecision(
                promote=True,
                source="structured_terminal",
                rule_id=HOUSING_CALL_COMPLETED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_structured_terminal",
            )
        if status == "failed":
            return PromotionDecision(
                promote=True,
                source="structured_terminal",
                rule_id=HOUSING_CALL_FAILED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_structured_terminal",
            )
        return PromotionDecision(
            promote=False,
            source=None,
            rule_id="",
            issue_id=None,
            reject_reason="weak_signal",
            success_reason="",
        )


def parse_housing_call_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[NormalizedCandidate], str]:
    _ = scene_state
    if not isinstance(move, dict):
        return [], "no_candidate"
    updates = move.get("scene_state_updates", {})
    if not isinstance(updates, dict):
        return [], "no_candidate"

    raw = updates.get("housing_call_outcome")
    raw_candidates: list[Any] = []
    if isinstance(raw, dict):
        raw_candidates.append(raw)
    elif isinstance(raw, list):
        raw_candidates.extend(raw)
    if not raw_candidates:
        return [], "no_candidate"

    normalized: list[dict[str, str]] = []
    saw_invalid_status = False
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", "") or "").strip().lower()
        if not status:
            continue
        if status not in HOUSING_CALL_TERMINAL_STATUSES:
            saw_invalid_status = True
            continue
        row = {"status": status}
        if row not in normalized:
            normalized.append(row)

    if not normalized:
        if saw_invalid_status:
            return [], "invalid_status"
        return [], "no_candidate"

    return (
        [
            NormalizedCandidate(
                aspect_id=COMMUNICATION_HOUSING_CALL_ASPECT_ID,
                subject_id="scene",
                value={"status": row["status"]},
            )
            for row in normalized
        ],
        "",
    )


def _housing_call_slot_key_fn(candidate: NormalizedCandidate) -> str:
    return encode_slot_key(candidate.aspect_id, "scene")


def _housing_call_build_outcome_id(
    candidate: NormalizedCandidate, turn_index: int, source_event_id: str
) -> str:
    event_fragment = _normalize_outcome_fragment(source_event_id or f"turn_{turn_index}")
    status_fragment = _normalize_outcome_fragment(candidate.value.get("status", ""))
    return f"resolved_communication_housing_call_scene_{status_fragment}_{event_fragment}"


def _housing_call_is_revocation(candidate: NormalizedCandidate) -> bool:
    _ = candidate
    return False


class MedicalSuppressantFormulationPromotionPolicy:
    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision:
        _ = ctx
        status = str(candidate.value.get("status", "") or "").strip()
        if status == "compatible":
            return PromotionDecision(
                promote=True,
                source="structured_attribute",
                rule_id=SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_structured_attribute",
            )
        if status == "incompatible":
            return PromotionDecision(
                promote=True,
                source="structured_attribute",
                rule_id=SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_structured_attribute",
            )
        return PromotionDecision(
            promote=False,
            source=None,
            rule_id="",
            issue_id=None,
            reject_reason="weak_signal",
            success_reason="",
        )


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


def parse_suppressant_formulation_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[NormalizedCandidate], str]:
    _ = scene_state
    if not isinstance(move, dict):
        return [], "no_candidate"
    updates = move.get("scene_state_updates", {})
    if not isinstance(updates, dict):
        return [], "no_candidate"

    raw = updates.get("suppressant_formulation_outcome")
    raw_candidates: list[Any] = []
    if isinstance(raw, dict):
        raw_candidates.append(raw)
    elif isinstance(raw, list):
        raw_candidates.extend(raw)
    if not raw_candidates:
        return [], "no_candidate"

    normalized: list[dict[str, str]] = []
    saw_invalid_status = False
    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        subject_id = str(item.get("subject_id", item.get("subject", "")) or "").strip()
        status = str(item.get("status", "") or "").strip().lower()
        if not subject_id or not status:
            continue
        if status not in SUPPRESSANT_FORMULATION_STATUSES:
            saw_invalid_status = True
            continue
        row = {"subject_id": subject_id, "status": status}
        if row not in normalized:
            normalized.append(row)

    if not normalized:
        if saw_invalid_status:
            return [], "invalid_status"
        return [], "no_candidate"

    return (
        [
            NormalizedCandidate(
                aspect_id=MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID,
                subject_id=row["subject_id"],
                value={"status": row["status"]},
            )
            for row in normalized
        ],
        "",
    )


def _suppressant_formulation_slot_key_fn(candidate: NormalizedCandidate) -> str:
    return encode_slot_key(candidate.aspect_id, candidate.subject_id)


def _suppressant_formulation_build_outcome_id(
    candidate: NormalizedCandidate, turn_index: int, source_event_id: str
) -> str:
    event_fragment = _normalize_outcome_fragment(source_event_id or f"turn_{turn_index}")
    subject_fragment = _normalize_outcome_fragment(candidate.subject_id)
    status_fragment = _normalize_outcome_fragment(candidate.value.get("status", ""))
    return (
        "resolved_medical_suppressant_formulation_"
        f"{subject_fragment}_{status_fragment}_{event_fragment}"
    )


def _suppressant_formulation_is_revocation(candidate: NormalizedCandidate) -> bool:
    _ = candidate
    return False


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

COMMUNICATION_HOUSING_CALL_SPEC = AspectSpec(
    aspect_id=COMMUNICATION_HOUSING_CALL_ASPECT_ID,
    outcome_class="communication",
    legacy_category="communication_state",
    legacy_key="housing_call",
    parse_candidates=parse_housing_call_outcome_candidates,
    slot_key_fn=_housing_call_slot_key_fn,
    build_outcome_id=_housing_call_build_outcome_id,
    is_revocation=_housing_call_is_revocation,
    promotion_policy=CommunicationHousingCallPromotionPolicy(),
    superseded_reason="superseded_terminal_outcome",
    revoked_reason="revoked",
)

MEDICAL_SUPPRESSANT_FORMULATION_SPEC = AspectSpec(
    aspect_id=MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID,
    outcome_class="medical",
    legacy_category="medical",
    legacy_key="suppressant_formulation",
    parse_candidates=parse_suppressant_formulation_outcome_candidates,
    slot_key_fn=_suppressant_formulation_slot_key_fn,
    build_outcome_id=_suppressant_formulation_build_outcome_id,
    is_revocation=_suppressant_formulation_is_revocation,
    promotion_policy=MedicalSuppressantFormulationPromotionPolicy(),
    superseded_reason="superseded_compatibility_state",
    revoked_reason="revoked",
    conflicting_candidates_reason="competing_same_turn_subject_status",
)

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


def parse_scene_commitment_outcome_candidates(
    move: dict[str, Any], scene_state: Any
) -> tuple[list[NormalizedCandidate], str]:
    _ = scene_state
    if not isinstance(move, dict):
        return [], "no_candidate"
    updates = move.get("scene_state_updates", {})
    if not isinstance(updates, dict):
        return [], "no_candidate"
    raw = updates.get("transactional_commitment")
    raw_list: list[Any] = []
    if isinstance(raw, dict):
        raw_list.append(raw)
    elif isinstance(raw, list):
        raw_list.extend(x for x in raw if isinstance(x, dict))
    if not raw_list:
        return [], "no_candidate"

    out: list[NormalizedCandidate] = []
    saw_invalid = False
    for item in raw_list:
        kind = _normalize_scene_commitment_token(
            str(item.get("kind", "") or ""), max_len=32
        )
        if kind not in SCENE_COMMITMENT_KINDS:
            saw_invalid = True
            continue
        subject_scope = _normalize_scene_commitment_token(
            str(item.get("subject_scope", "") or ""), max_len=64
        )
        if not subject_scope or subject_scope == "x":
            saw_invalid = True
            continue
        phase = str(item.get("phase", "") or "").strip().lower()
        if not phase or phase not in SCENE_COMMITMENT_PHASES:
            saw_invalid = True
            continue
        tid = str(item.get("thread_instance_id", "") or "").strip()
        prior = str(item.get("prior_thread_id", "") or "").strip()
        label = str(item.get("label", "") or "").strip()[:120]
        value: dict[str, str] = {
            "kind": kind,
            "subject_scope": subject_scope,
            "phase": phase,
        }
        if tid:
            value["thread_instance_id"] = tid
        if prior:
            value["prior_thread_id"] = prior
        if label:
            value["label"] = label
        out.append(
            NormalizedCandidate(
                aspect_id=TRANSACTION_SCENE_COMMITMENT_ASPECT_ID,
                subject_id=subject_scope,
                value=value,
            )
        )
    if not out:
        if saw_invalid:
            return [], "invalid_scene_commitment"
        return [], "no_candidate"
    return (out, "")


def _scene_commitment_slot_key_fn(candidate: NormalizedCandidate) -> str:
    k = str(candidate.value.get("kind", "") or "").strip()
    sc = str(candidate.value.get("subject_scope", "") or "").strip()
    return f"{candidate.aspect_id}::{k}::{sc}"


def _scene_commitment_build_outcome_id(
    candidate: NormalizedCandidate, turn_index: int, source_event_id: str
) -> str:
    event_fragment = _normalize_outcome_fragment(
        source_event_id or f"turn_{turn_index}"
    )
    k = _normalize_outcome_fragment(candidate.value.get("kind", ""))
    sc = _normalize_outcome_fragment(candidate.value.get("subject_scope", ""))
    ph = _normalize_outcome_fragment(candidate.value.get("phase", ""))
    tid = _normalize_outcome_fragment(candidate.value.get("thread_instance_id", ""))
    return (
        f"resolved_transaction_scene_{k}_{sc}_{ph}_{tid}_turn{turn_index}_{event_fragment}"
    )


def _scene_commitment_is_revocation(candidate: NormalizedCandidate) -> bool:
    return str(candidate.value.get("phase", "") or "").strip().lower() == "voided"


def merge_transaction_commitment_value_for_apply(
    raw: dict[str, str],
    *,
    active: Any,
    source_event_id: str,
    turn_index: int,
) -> dict[str, str]:
    """Deterministic value merge for persistence: thread mint, lineage, source ref."""
    v = {str(k): str(val) for k, val in raw.items() if isinstance(k, str)}
    v["source_event_id"] = str(source_event_id or "").strip()
    if not v.get("thread_instance_id", "").strip():
        if active is not None:
            av = getattr(active, "value", None) or {}
            if isinstance(av, dict):
                old = str(av.get("thread_instance_id", "") or "").strip()
                if old:
                    v["thread_instance_id"] = old
    if not v.get("thread_instance_id", "").strip():
        frag = _normalize_outcome_fragment(source_event_id or f"turn_{turn_index}")
        v["thread_instance_id"] = f"tc_{turn_index}_{frag}"
    if active is not None:
        av = getattr(active, "value", None) or {}
        if isinstance(av, dict):
            old_tid = str(av.get("thread_instance_id", "") or "").strip()
            new_tid = str(v.get("thread_instance_id", "") or "").strip()
            if old_tid and new_tid and old_tid != new_tid:
                v.setdefault("prior_thread_id", old_tid)
    return v


def transaction_commitment_semantic_equal(a: dict[str, str], b: dict[str, str]) -> bool:
    """No-op detection: kind, scope, phase, thread identity (ignores source_event_id drift)."""
    for k in ("kind", "subject_scope", "phase", "thread_instance_id"):
        if str(a.get(k, "") or "").strip() != str(b.get(k, "") or "").strip():
            return False
    return True


class TransactionSceneCommitmentPromotionPolicy:
    """Promote structured transactional commitments; `initiated` deferred for MVP."""

    def evaluate(
        self, candidate: NormalizedCandidate, ctx: PromotionContext
    ) -> PromotionDecision:
        _ = ctx
        phase = str(candidate.value.get("phase", "") or "").strip().lower()
        if phase == "initiated":
            return PromotionDecision(
                promote=False,
                source=None,
                rule_id="",
                issue_id=None,
                reject_reason="initiated_mvp_deferred",
                success_reason="",
            )
        if phase == "committed":
            return PromotionDecision(
                promote=True,
                source="structured_transactional_commitment",
                rule_id=SCENE_COMMITMENT_COMMITTED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_committed",
            )
        if phase == "awaiting_fulfillment":
            return PromotionDecision(
                promote=True,
                source="structured_transactional_commitment",
                rule_id=SCENE_COMMITMENT_AWAITING_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_awaiting_fulfillment",
            )
        if phase == "fulfilled":
            return PromotionDecision(
                promote=True,
                source="structured_transactional_commitment",
                rule_id=SCENE_COMMITMENT_FULFILLED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_fulfilled",
            )
        if phase == "failed":
            return PromotionDecision(
                promote=True,
                source="structured_transactional_commitment",
                rule_id=SCENE_COMMITMENT_FAILED_RULE_ID,
                issue_id=None,
                reject_reason="",
                success_reason="promoted_failed",
            )
        if phase == "voided":
            return PromotionDecision(
                promote=False,
                source=None,
                rule_id="",
                issue_id=None,
                reject_reason="voided_is_revocation_path",
                success_reason="",
            )
        return PromotionDecision(
            promote=False,
            source=None,
            rule_id="",
            issue_id=None,
            reject_reason="unknown_phase",
            success_reason="",
        )


TRANSACTION_SCENE_COMMITMENT_SPEC = AspectSpec(
    aspect_id=TRANSACTION_SCENE_COMMITMENT_ASPECT_ID,
    outcome_class="transaction",
    legacy_category="transaction",
    legacy_key="scene_commitment",
    parse_candidates=parse_scene_commitment_outcome_candidates,
    slot_key_fn=_scene_commitment_slot_key_fn,
    build_outcome_id=_scene_commitment_build_outcome_id,
    is_revocation=_scene_commitment_is_revocation,
    promotion_policy=TransactionSceneCommitmentPromotionPolicy(),
    superseded_reason="superseded_scene_commitment",
    revoked_reason="revoked_voided",
    conflicting_candidates_reason="competing_same_turn_scene_commitment",
)

ASPECT_REGISTRY: dict[str, AspectSpec] = {
    LODGING_SLEEP_SURFACE_ASPECT_ID: LODGING_SLEEP_SURFACE_SPEC,
    COMMUNICATION_HOUSING_CALL_ASPECT_ID: COMMUNICATION_HOUSING_CALL_SPEC,
    MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID: MEDICAL_SUPPRESSANT_FORMULATION_SPEC,
    ACCESS_LOCATION_ENTRY_ASPECT_ID: ACCESS_LOCATION_ENTRY_SPEC,
    TRANSACTION_SCENE_COMMITMENT_ASPECT_ID: TRANSACTION_SCENE_COMMITMENT_SPEC,
}
