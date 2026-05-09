"""Medical suppressant-formulation resolved outcome aspect (registry-owned)."""

from __future__ import annotations

from typing import Any

from resolved_outcome_normalize import _normalize_outcome_fragment, encode_slot_key
from resolved_outcome_spec import (
    AspectSpec,
    NormalizedCandidate,
    PromotionContext,
    PromotionDecision,
)

MEDICAL_SUPPRESSANT_FORMULATION_ASPECT_ID = "medical.suppressant_formulation"

SUPPRESSANT_FORMULATION_COMPATIBLE_RULE_ID = (
    "medical.suppressant_formulation.compatible.v1"
)
SUPPRESSANT_FORMULATION_INCOMPATIBLE_RULE_ID = (
    "medical.suppressant_formulation.incompatible.v1"
)

SUPPRESSANT_FORMULATION_STATUSES = frozenset({"compatible", "incompatible"})


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
