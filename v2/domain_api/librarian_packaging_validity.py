"""Packaging validity gate for LibrarianKnowledgeBundle (#34 S2b).

Packaging consumes already-produced bundles; it never triggers Librarian regeneration.
"""

from __future__ import annotations

from dataclasses import dataclass

from .librarian_contract import LibrarianKnowledgeBundle


@dataclass(frozen=True)
class PackagingBindingContext:
    """Host binding state at manifest assembly time."""

    hg_round_id: str
    turn_index: int
    pipeline_stage: str
    continuity_version: int
    authoritative_snapshot_id: str
    domain_commit_id: str | None = None
    bound_character_id: str | None = None


@dataclass(frozen=True)
class PackagingEligibility:
    accepted: bool
    reason: str
    rejection_codes: tuple[str, ...] = ()


def assess_bundle_packaging_eligibility(
    bundle: LibrarianKnowledgeBundle,
    context: PackagingBindingContext,
) -> PackagingEligibility:
    if bundle.degradation.level == "unavailable":
        return PackagingEligibility(
            accepted=False,
            reason="bundle unavailable",
            rejection_codes=("degradation_unavailable",),
        )

    validity = bundle.validity
    codes: list[str] = []

    if validity.bound_hg_round_id != context.hg_round_id:
        codes.append("round_mismatch")

    if _snapshot_stale(validity.valid_from_authoritative_snapshot_id, context.authoritative_snapshot_id):
        codes.append("authoritative_snapshot_stale")

    for key in validity.invalidation_keys:
        if key.key_kind == "continuity_version" and key.key_value != str(context.continuity_version):
            codes.append("continuity_version_stale")
        if key.key_kind == "hg_round_id" and key.key_value != context.hg_round_id:
            codes.append("invalidation_round_mismatch")

    if validity.validity_scope == "stage_current":
        if validity.bound_turn_index != context.turn_index:
            codes.append("turn_index_mismatch")
        if validity.bound_pipeline_stage and validity.bound_pipeline_stage != context.pipeline_stage:
            codes.append("pipeline_stage_mismatch")

    if validity.bound_domain_commit_id:
        if not context.domain_commit_id:
            codes.append("domain_commit_required")
        elif validity.bound_domain_commit_id != context.domain_commit_id:
            codes.append("domain_commit_mismatch")

    if context.bound_character_id and bundle.consumer_role == "character":
        evidence = bundle.audit.structured_mediation_evidence or {}
        bound_consumer = str(evidence.get("consumer_instance_id") or "").strip()
        if bound_consumer and bound_consumer != context.bound_character_id:
            codes.append("character_binding_mismatch")

    if codes:
        return PackagingEligibility(
            accepted=False,
            reason="bundle stale or mismatched for packaging context",
            rejection_codes=tuple(dict.fromkeys(codes)),
        )

    return PackagingEligibility(accepted=True, reason="eligible")


def _snapshot_stale(bundle_snapshot: str, context_snapshot: str) -> bool:
    bundle_snapshot = str(bundle_snapshot or "").strip()
    context_snapshot = str(context_snapshot or "").strip()
    if not bundle_snapshot or not context_snapshot:
        return False
    return bundle_snapshot != context_snapshot
