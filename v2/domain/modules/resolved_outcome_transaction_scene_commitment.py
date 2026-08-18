"""Transactional scene-commitment resolved outcome aspect (GitHub #127).

Semantic slot identity: ``kind`` + ``subject_scope``; lineage in outcome ``value``.
"""

from __future__ import annotations

from typing import Any

from resolved_outcome_normalize import _normalize_outcome_fragment, _normalize_scene_commitment_token
from resolved_outcome_spec import (
    AspectSpec,
    NormalizedCandidate,
    PromotionContext,
    PromotionDecision,
)

TRANSACTION_SCENE_COMMITMENT_ASPECT_ID = "transaction.scene_commitment"

SCENE_COMMITMENT_COMMITTED_RULE_ID = "transaction.scene_commitment.committed.v1"
SCENE_COMMITMENT_AWAITING_RULE_ID = "transaction.scene_commitment.awaiting_fulfillment.v1"
SCENE_COMMITMENT_FULFILLED_RULE_ID = "transaction.scene_commitment.fulfilled.v1"
SCENE_COMMITMENT_FAILED_RULE_ID = "transaction.scene_commitment.failed.v1"

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
