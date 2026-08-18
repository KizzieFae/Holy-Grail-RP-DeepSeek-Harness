"""Generic resolved-outcome application (registry-driven, deterministic)."""

from __future__ import annotations

from typing import Any

from continuity_state import ResolvedOutcome
from resolved_outcome_registry import (
    ASPECT_REGISTRY,
    PromotionContext,
    TRANSACTION_SCENE_COMMITMENT_ASPECT_ID,
    merge_transaction_commitment_value_for_apply,
    transaction_commitment_semantic_equal,
)


def _find_active_outcome_for_slot(manager: Any, slot_key: str) -> ResolvedOutcome | None:
    for outcome in reversed(getattr(manager, "resolved_outcomes", [])):
        if getattr(outcome, "status", "") != "active":
            continue
        if str(getattr(outcome, "slot_key", "") or "") == slot_key:
            return outcome
    return None


def _new_debug(reason: str = "no_candidate") -> dict[str, Any]:
    return {
        "candidate": None,
        "candidate_source": None,
        "decision": "none",
        "reason": reason,
        "outcome_id": None,
        "supersedes_outcome_id": None,
        "issue_id": None,
    }


def _apply_candidate(
    *,
    manager: Any,
    aspect_id: str,
    spec: Any,
    candidate: Any,
    promo_ctx: PromotionContext,
    source_event_id: str,
    turn_index: int,
    debug: dict[str, Any],
) -> None:
    if candidate.aspect_id != aspect_id:
        debug["reason"] = "unknown_aspect_id"
        return

    debug["candidate"] = dict(candidate.value)
    slot_key = spec.slot_key_fn(candidate)
    active = _find_active_outcome_for_slot(manager, slot_key)

    if spec.is_revocation(candidate):
        if active is None:
            debug["reason"] = "no_active_outcome_to_revoke"
            return
        active.status = "revoked"
        active.revoked_turn_index = turn_index
        debug["decision"] = "revoked"
        debug["reason"] = spec.revoked_reason
        debug["outcome_id"] = active.outcome_id
        return

    if aspect_id == TRANSACTION_SCENE_COMMITMENT_ASPECT_ID:
        merged = merge_transaction_commitment_value_for_apply(
            dict(candidate.value),
            active=active,
            source_event_id=source_event_id,
            turn_index=turn_index,
        )
        if active is not None and transaction_commitment_semantic_equal(
            active.value, merged
        ):
            debug["reason"] = "no_op_existing_value"
            debug["outcome_id"] = active.outcome_id
            return
    elif active is not None and dict(active.value) == dict(candidate.value):
        debug["reason"] = "no_op_existing_value"
        debug["outcome_id"] = active.outcome_id
        return

    decision = spec.promotion_policy.evaluate(candidate, promo_ctx)
    if not decision.promote:
        debug["reason"] = decision.reject_reason or "weak_signal"
        return

    debug["candidate_source"] = decision.source
    debug["issue_id"] = decision.issue_id

    final_value: dict[str, str] = (
        merge_transaction_commitment_value_for_apply(
            dict(candidate.value),
            active=active,
            source_event_id=source_event_id,
            turn_index=turn_index,
        )
        if aspect_id == TRANSACTION_SCENE_COMMITMENT_ASPECT_ID
        else dict(candidate.value)
    )
    outcome = ResolvedOutcome(
        outcome_id=spec.build_outcome_id(candidate, turn_index, source_event_id),
        category=spec.legacy_category,
        key=spec.legacy_key,
        subject_id=candidate.subject_id,
        value=final_value,
        status="active",
        source_event_id=source_event_id,
        source_issue_id=decision.issue_id,
        rule_id=decision.rule_id,
        supersedes_outcome_id=active.outcome_id if active is not None else None,
        created_turn_index=turn_index,
        aspect_id=aspect_id,
        slot_key=slot_key,
    )
    if active is not None:
        active.status = "superseded"
        active.superseded_turn_index = turn_index
    getattr(manager, "resolved_outcomes", []).append(outcome)
    debug["decision"] = "superseded" if active is not None else "promoted"
    debug["reason"] = (
        spec.superseded_reason if active is not None else decision.success_reason
    )
    debug["outcome_id"] = outcome.outcome_id
    debug["supersedes_outcome_id"] = outcome.supersedes_outcome_id


def apply_registered_resolved_outcomes(
    *,
    manager: Any,
    move: dict[str, Any],
    event: Any,
    turn_consequences: dict[str, Any],
    turn_index: int,
) -> dict[str, dict[str, Any]]:
    """Apply all registered aspects for this move and return debug by legacy key."""
    scene_state = getattr(manager, "scene_state", None)
    consequence_tags = frozenset(
        str(item) for item in turn_consequences.get("tags", []) if str(item).strip()
    )
    promo_ctx = PromotionContext(
        turn_index=turn_index,
        consequence_tags=consequence_tags,
        manager=manager,
    )
    source_event_id = str(getattr(event, "event_id", "") or "")

    debug_by_key: dict[str, dict[str, Any]] = {
        spec.legacy_key: _new_debug() for spec in ASPECT_REGISTRY.values()
    }

    for aspect_id, spec in ASPECT_REGISTRY.items():
        candidates, reason = spec.parse_candidates(move, scene_state)
        debug = debug_by_key[spec.legacy_key]
        debug["reason"] = reason or "no_candidate"
        if not candidates:
            continue

        slot_to_value: dict[str, dict[str, str]] = {}
        duplicate_slot_reason: str | None = None
        for candidate in candidates:
            slot_key = spec.slot_key_fn(candidate)
            prev = slot_to_value.get(slot_key)
            if prev is not None:
                duplicate_slot_reason = (
                    spec.conflicting_candidates_reason
                    if prev != candidate.value
                    else "multiple_candidates_unsupported"
                )
                break
            slot_to_value[slot_key] = dict(candidate.value)
        if duplicate_slot_reason is not None:
            debug["reason"] = duplicate_slot_reason
            continue

        for candidate in candidates:
            _apply_candidate(
                manager=manager,
                aspect_id=aspect_id,
                spec=spec,
                candidate=candidate,
                promo_ctx=promo_ctx,
                source_event_id=source_event_id,
                turn_index=turn_index,
                debug=debug,
            )

    return debug_by_key
